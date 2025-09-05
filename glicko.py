import math

# ---------- 2.0~5.0 与 Glicko 评分映射 ----------
def _to_r(score: float) -> float:
    return 1000.0 + (score - 2.0) * 300.0

def _to_score(r: float) -> float:
    return 2.0 + (r - 1000.0) / 300.0

# ---------- Glicko-2 基础 ----------
SCALE = 173.7178

def _to_mu_phi(r, rd):
    return (r - 1500.0) / SCALE, rd / SCALE

def _from_mu_phi(mu, phi):
    return mu * SCALE + 1500.0, phi * SCALE

def _g(phi):
    return 1.0 / math.sqrt(1.0 + 3.0 * (phi**2) / (math.pi**2))

def _E(mu, mu_j, phi_j):
    return 1.0 / (1.0 + math.exp(-_g(phi_j) * (mu - mu_j)))

def _rd_from_sets(season_sets: int) -> float:
    # 无状态近似：盘数越多，RD 越小（更确定）
    rd = 350.0 * math.exp(-season_sets / 20.0)
    return max(60.0, min(350.0, rd))

def _parse_set_score(txt: str) -> tuple[int, int]:
    for sep in ("-", ":", " "):
        if sep in txt:
            a, b = txt.split(sep)
            return int(a.strip()), int(b.strip())
    raise ValueError("比分格式应为 '6-4' / '10-7' / '7:5' 等")

# ---------- 单盘为一个“评级周期”的加权 Glicko-2 更新 ----------
def _glicko2_update_one_game(r, rd, sigma, opp_r, opp_rd, result, weight,
                             tau=0.5, rd_min=30.0, rd_max=350.0,
                             mu_for_expect=None):
    """
    r, rd, sigma: 本人当前 Glicko 参数
    opp_r, opp_rd: 对手当前 Glicko 参数
    result: 1.0(胜) / 0.0(负)
    weight: 本盘权重（含单双打/抢十/比分差）
    mu_for_expect: 若提供，则仅在计算 E（期望）时用它替代本人 mu（用于“女性 -0.5”修正）
    """
    mu,  phi  = _to_mu_phi(r, rd)
    mu_j,phi_j= _to_mu_phi(opp_r, opp_rd)

    # 期望 E：允许用“修正后的 mu”只影响期望（女性 -0.5 只影响期望，不改变本人基础 mu）
    mu_eff = mu if mu_for_expect is None else mu_for_expect
    E_  = _E(mu_eff, mu_j, phi_j)
    g_  = _g(phi_j)

    # v 与 delta（加权）
    v   = 1.0 / (weight * (g_**2) * E_ * (1.0 - E_) + 1e-12)
    delta = v * (weight * g_ * (result - E_))

    # 求新 sigma
    a = math.log(sigma**2)
    def f(x):
        ex = math.exp(x)
        num = ex * (delta**2 - phi**2 - v - ex)
        den = 2.0 * (phi**2 + v + ex)**2
        return (num/den) - (x - a) / (tau**2)

    A = a
    if delta**2 > (phi**2 + v):
        B = math.log(delta**2 - phi**2 - v)
    else:
        k = 1
        while f(a - k * tau) < 0:
            k += 1
        B = a - k * tau

    fA, fB = f(A), f(B)
    eps = 1e-6
    while abs(B - A) > eps:
        C = A + (A - B) * fA / (fB - fA)
        fC = f(C)
        if fC * fB < 0:
            A, fA = B, fB
        else:
            fA = fA / 2.0
        B, fB = C, fC
    new_sigma = math.exp(A / 2.0)

    # 新 RD & rating
    phi_star  = math.sqrt(phi**2 + new_sigma**2)
    phi_prime = 1.0 / math.sqrt((1.0 / (phi_star**2)) + (1.0 / v))
    mu_prime  = mu + (phi_prime**2) * (weight * _g(phi_j) * (result - E_))

    new_r, new_rd = _from_mu_phi(mu_prime, phi_prime)
    new_rd = min(rd_max, max(rd_min, new_rd))
    return new_r, new_rd, new_sigma

# ---------- 你要调用的唯一函数 ----------
def update_user_score_glicko2(
    user_score: float,          # 2.0~5.0（若双打你已传队友均值）
    opp_score: float,           # 2.0~5.0（若双打传对方队内均值）
    user_is_female: bool,       # 女=True / 男=False（只影响期望）
    user_win: bool,             # 本盘胜负 True/False
    user_season_sets: int,      # 本赛季已打盘数（用来近似 RD）
    set_score: str,             # "6-4" / "7:5" / "10-7"（>=10 视为抢十）
    match_type: str             # "单打" / "双打"
) -> float:
    # 1) 基础映射
    r_user = _to_r(user_score)
    r_opp  = _to_r(opp_score)

    # 2) RD/σ（无状态近似）
    rd_user = _rd_from_sets(user_season_sets)
    sigma_user = 0.06
    rd_opp  = 80.0   # 对手 RD 不可得时的稳态近似

    # 3) 权重：单双打/抢十/比分差
    w = 1.0
    if match_type.strip() == "双打":
        w *= 0.85
    a, b = _parse_set_score(set_score)
    if max(a, b) >= 10:
        w *= 0.60
    # 比分差加权（最多 +20%）
    m = 1.0 + max(0.0, min((abs(a - b) - 2) * 0.05, 0.20))
    w *= m

    # 4) 女性修正：只影响期望（把用户分数临时 -0.5 再映射）
    mu_eff = None
    if user_is_female:
        r_eff = _to_r(max(2.0, user_score - 0.5))
        mu_eff, _ = _to_mu_phi(r_eff, rd_user)

    # 5) 跑一次“单盘评级周期”更新
    result = 1.0 if user_win else 0.0
    r_new, rd_new, sigma_new = _glicko2_update_one_game(
        r_user, rd_user, sigma_user,
        r_opp, rd_opp,
        result, w,
        mu_for_expect=mu_eff
    )

    # 6) 回到 2.0~5.0，并夹在边界；两位小数
    score_new = _to_score(r_new)
    return float(max(2.0, min(5.0, round(score_new, 2))))

"""
# 单打：用户3.5，对手3.8；用户为女；本盘6-4获胜；本季已打5盘
print(update_user_score_glicko2(3.5, 3.8, True, True, 5, "6-4", "单打"))
# 双打：用户3.5（队内均值），对手3.6（队内均值）；本盘10-7获胜
print(update_user_score_glicko2(3.5, 3.6, False, True, 12, "10-7", "双打"))
"""