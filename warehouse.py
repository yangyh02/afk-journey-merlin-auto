from common import screenshot_bgr, wait_and_click, get_template_path, get_work_path, get_templates_dir, load_template
import cv2
import os
import time
import numpy as np
from typing import Optional


# === 模板路径（需要你自己准备对应截图）===
# 进入英雄厅堂仓库用的按钮 ck
tpl_ck = get_template_path("ck.png")

# 仓库界面顶部标题（例如"赛季共鸣等级："附近的一块稳定区域）
tpl_warehouse_title = get_template_path("warehouse_title.png")

# 第一行第一列卡片的锚点（比如整张卡或左上角花边）
tpl_first_card_anchor = get_template_path("warehouse_first_card.png")

# 初始界面和拖动后界面都会出现、但在拖动动画中会跟着移动的那一行说明文字
# 例如"同时受到共鸣之脉+184的全部属性影响"附近的一小块，这里命名为 relevel
tpl_relevel = get_template_path("relevel.png")

# 共鸣之手下方 5 个位置的锚点（整块区域中上部的一小块），用于读取初始 5 个角色
tpl_rehand = get_template_path("rehand.png")

# 打开"选择种族/职业"界面的按钮 catalog
tpl_catalog = get_template_path("catalog.png")

# 过滤界面中，"共鸣骑士"行的锚点 reknight（其下方是要读取的角色）
tpl_reknight = get_template_path("reknight.png")

# 退出按钮 exit（离开仓库）
tpl_exit = get_template_path("exitck.png")

# 种族模板（yg，ly，mx，wl，bs，em，xk）
RACE_TEMPLATES = {
    "yg": get_template_path("yg.png"),
    "ly": get_template_path("ly.png"),
    "mx": get_template_path("mx.png"),
    "wl": get_template_path("wl.png"),
    "bs": get_template_path("bs.png"),
    "em": get_template_path("em.png"),
    "xk": get_template_path("xk.png"),
}

# 职业模板（tk，fz，ss，fs，yx，zs）
JOB_TEMPLATES = {
    "tk": get_template_path("tk.png"),
    "fz": get_template_path("fz.png"),
    "ss": get_template_path("ss.png"),
    "fs": get_template_path("fs.png"),
    "yx": get_template_path("yx.png"),
    "zs": get_template_path("zs.png"),
}

TEMPLATE_DIR = get_templates_dir()

# 角色头像模板库：同一个英雄可以有多个头像（皮肤）
# key：英雄名（使用你给的图片基础名，如 'nvyao'）
# val：该英雄所有头像模板路径列表（包括皮肤，如 'nvyao2' 等）
HERO_TEMPLATES = {}

# 你提供的所有角色基础名（不带皮肤后缀 2）
ALL_HERO_NAMES = [
    "nvyao",
    "heifa",
    "renhuang",
    "huohuli",
    "luxi",
    "douduo",
    "wuyue",
    "mankala",
    "ade",
    "bailang",
    "baonv",
    "beila",
    "bingmo",
    "boluotou",
    "boni",
    "cangbai",
    "chuanzhang",
    "daimeng",
    "dashu",
    "fei",
    "fenghuang",
    "fushen",
    "fuxiong",
    "gongshen",
    "gouzi",
    "guangdun",
    "guanggong",
    "gubian",
    "guicao",
    "gunge",
    "gungun",
    "guwang",
    "gushe",
    "heibao",
    "heye",
    "huajie",
    "huanv",
    "hudie",
    "hujin",
    "huonv",
    "jiala",
    "jianshen",
    "jingji",
    "jiushen",
    "jiuwei",
    "kafula",
    "kaka",
    "kelin",
    "kuishen",
    "kululu",
    "laiousi",
    "langren",
    "laoshi",
    "laoyang",
    "luka",
    "lvjian",
    "malu",
    "manman",
    "mangmang",
    "maonv",
    "matong",
    "meimo",
    "mengshen",
    "mubei",
    "nafei",
    "naiba",
    "nanqiang",
    "nazi",
    "niaoren",
    "nilu",
    "nvqi",
    "panduola",
    "paomo",
    "popo",
    "renma",
    "shaliye",
    "shangren",
    "shaoye",
    "shayu",
    "shixianggui",
    "shizi",
    "shuangzi",
    "shuifa",
    "sishou",
    "tiaotiao",
    "tugong",
    "luosang",
    "walika",
    "weila",
    "weilun",
    "xiaochou",
    "xiaoyang",
    "xida",
    "xiezi",
    "xinbada",
    "xiniu",
    "xiu",
    "geerda",
    "xiongmao",
    "xuenv",
    "yi",
    "yindue",
    "zhongshen",
    "tianfa",
    "donghou",
    "songshu",
    "xiaolunv",
    "zuya",
    "xinmeier",
    "fulilian",
    "yifu",
    "huopu",
    "shumo",
    "longgong",
    "niaoshen",
    "renyu",
    "peiji",
    "liuyan",
    "luolan",
    "wangzi",
    "manniao",
    "aidejia",
    "sainie",
    "xing"
]

# 识别结果输出路径（文本文件）
WAREHOUSE_TXT_PATH = get_work_path("warehouse_heroes.txt")


def init_templates_from_dir():
    """
    根据 F:\\afkj\\game-bot\\templates 目录下的图片，自动填充：
    - HERO_TEMPLATES：支持皮肤（同一角色的 xxx2、xxx3 等都会归并到同一个 key）
    """
    global HERO_TEMPLATES

    HERO_TEMPLATES.clear()
    HERO_TEMPLATES.update({name: [] for name in ALL_HERO_NAMES})

    if not os.path.isdir(TEMPLATE_DIR):
        print(f"模板目录不存在：{TEMPLATE_DIR}")
        return

    for fname in os.listdir(TEMPLATE_DIR):
        fpath = os.path.join(TEMPLATE_DIR, fname)
        if not os.path.isfile(fpath):
            continue

        lower = fname.lower()
        if not (lower.endswith(".png") or lower.endswith(".jpg") or lower.endswith(".jpeg")):
            continue

        name_no_ext, _ = os.path.splitext(fname)

        # 处理角色模板：例如 nvyao.png, nvyao2.png 等
        for hero_name in ALL_HERO_NAMES:
            # 规则（按你的要求收紧）：
            # - 仅合并“纯数字后缀”的皮肤/变体：wuyue2 -> wuyue
            # - 若是字母后缀（可能重名/不同人），不合并：wuyuea 不算 wuyue
            if name_no_ext == hero_name:
                HERO_TEMPLATES.setdefault(hero_name, []).append(fpath)
                break

            if name_no_ext.startswith(hero_name):
                suffix = name_no_ext[len(hero_name):]
                if suffix.isdigit():
                    HERO_TEMPLATES.setdefault(hero_name, []).append(fpath)
                    break
                # 字母/其他后缀：不合并到基础名，继续尝试匹配下一个 hero_name


# === 布局参数：需要根据你的实际截图适当微调 ===
NUM_COLS = 6          # 骑士行一行最多 6 列卡片
CARD_WIDTH = 75       # 基础卡片宽度估值（供骑士使用）
CARD_HEIGHT = 100     # 单个卡片高度估值
COL_GAP = 10          # 骑士之间水平间距
ROW_GAP = 10          # 行之间垂直间距
MAX_ROWS = 2          # 共鸣骑士最多读取 2 行

# 是否把每个卡槽截图保存到 debug 目录，方便校对框位置
DEBUG_SAVE_SLOTS = True

# 拖动参数：在仓库可滚动区域按住并向上拖动一段距离，让列表下移到“三行半”视图
# 可以适当设置得“粗暴”一点，只要拖过去即可，拖过头没关系
DRAG_DISTANCE = 700   # 像素，向上拖动距离，需要你按实际屏幕微调

# 给 AHK 发送拖动指令用的文件路径（由 AHK 完成实际鼠标拖动）
DRAG_COORD_PATH = get_work_path("shared\\drag_coord.txt")

# 从各个锚点到第一张卡片左上角的“微调”偏移。
# 主要用于在已经按“左对齐、紧贴下边缘”计算出的基础上，再稍微修一点点。
HAND_FIRST_OFFSET_X = 0      # rehand -> 共鸣之手第一张卡片左上角微调（正数往右，负数往左）
HAND_FIRST_OFFSET_Y = 0      # rehand -> 共鸣之手第一张卡片左上角微调（正数往下，负数往上）
KNIGHT_FIRST_OFFSET_X = 0    # reknight -> 共鸣骑士第一张卡片左上角微调
KNIGHT_FIRST_OFFSET_Y = 0


def _match_template(img, template_path, threshold=0.8):
    """在整张 img 上做模板匹配，返回匹配中心坐标或 None。"""
    if not os.path.exists(template_path):
        print(f"模板不存在: {template_path}")
        return None

    template = load_template(template_path)
    if template is None:
        print(f"模板读取失败: {template_path}")
        return None

    th, tw = template.shape[:2]
    ih, iw = img.shape[:2]
    if ih < th or iw < tw:
        print("截图尺寸小于模板尺寸，无法匹配。")
        return None

    res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    print(f"{os.path.basename(template_path)} 匹配得分: {max_val:.3f}")
    if max_val < threshold:
        return None

    cx = max_loc[0] + tw // 2
    cy = max_loc[1] + th // 2
    return cx, cy


def _match_template_with_box(img, template_path, threshold=0.8):
    """
    在整张 img 上做模板匹配，返回 (cx, cy, tw, th) 或 None：
    - (cx, cy): 模板匹配到的中心点
    - (tw, th): 模板自身的宽高，用来推算“左边界 / 下边界”
    """
    if not os.path.exists(template_path):
        print(f"模板不存在: {template_path}")
        return None

    template = load_template(template_path)
    if template is None:
        print(f"模板读取失败: {template_path}")
        return None

    th, tw = template.shape[:2]
    ih, iw = img.shape[:2]
    if ih < th or iw < tw:
        print("截图尺寸小于模板尺寸，无法匹配。")
        return None

    res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    print(f"{os.path.basename(template_path)}(with_box) 匹配得分: {max_val:.3f}")
    if max_val < threshold:
        return None

    cx = max_loc[0] + tw // 2
    cy = max_loc[1] + th // 2
    return cx, cy, tw, th


def _locate_first_card(img):
    """
    定位当前屏幕上第一行第一列卡片的大致左上角坐标。
    优先用 first_card_anchor 模板；找不到时，可退化为根据标题估算。
    """
    pos = _match_template(img, tpl_first_card_anchor, threshold=0.8)
    if pos:
        cx, cy = pos
        x0 = int(cx - CARD_WIDTH / 2)
        y0 = int(cy - CARD_HEIGHT / 2)
        return x0, y0

    title_pos = _match_template(img, tpl_warehouse_title, threshold=0.8)
    if not title_pos:
        print("无法定位仓库标题或第一张卡片锚点。")
        return None

    tx, ty = title_pos
    # 这里的偏移要你根据实际界面调：
    # 标题下方到第一行卡片的垂直距离、大概水平偏移等
    x0 = tx - 300
    y0 = ty + 150
    return x0, y0


def _locate_scroll_anchor_y(img):
    """
    定位那一行“不会再移动的说明文字”的纵坐标，用于判断是否已经处于拖动后的稳定界面。
    返回 (cx, cy) 或 None。
    """
    return _match_template(img, tpl_relevel, threshold=0.8)


def send_drag(x1: int, y1: int, x2: int, y2: int):
    """
    将一次拖动指令写入文件，交给 AHK 脚本执行：
    AHK 会从 (x1, y1) 移动、按下左键，拖到 (x2, y2) 后松开。
    """
    with open(DRAG_COORD_PATH, "w", encoding="utf-8") as f:
        f.write(f"{x1} {y1} {x2} {y2}")


def _extract_card_roi(img, row, col, x0, y0,
                      card_width: int, card_height: int,
                      col_gap: int, row_gap: int):
    """根据行列索引和首卡坐标，截取单个卡片区域。支持自定义卡片宽高和间距。"""
    x = x0 + col * (card_width + col_gap)
    y = y0 + row * (card_height + row_gap)
    ih, iw = img.shape[:2]
    if x < 0 or y < 0 or x + card_width > iw or y + card_height > ih:
        return None
    return img[y:y + card_height, x:x + card_width]


HERO_MATCH_THRESHOLD = 0.6    # 英雄头像匹配阈值（原来是 0.75，可按需要再调）

# 头像识别：多尺度模板匹配（解决不同分辨率/缩放导致头像大小不一致）
# - 你可以直接改这里的缩放范围与步进
HERO_TEMPLATE_SCALE_MIN = 0.90
HERO_TEMPLATE_SCALE_MAX = 1.10
HERO_TEMPLATE_SCALE_STEP = 0.05

# 边框识别（按你的新规则）：
# - 只取卡片最上方 8% 条带做 Canny
# - edge_count > 50 => 有边框（高）
# - 否则 => 无边框（低）
BORDER_TOP_RATIO = 0.08
BORDER_EDGE_THRESHOLD = 50


def _iter_scales(min_s: float, max_s: float, step: float):
    if step <= 0:
        return
    s = float(min_s)
    # 用 +1e-9 避免浮点误差导致漏掉 max_s
    while s <= float(max_s) + 1e-9:
        yield round(s, 4)
        s += float(step)


def _best_multiscale_match_score(search_bgr, template_bgr) -> float:
    """
    在 search_bgr 上对 template_bgr 做多尺度匹配，返回最佳得分（TM_CCOEFF_NORMED）。
    只做评分，不返回位置；用于“选出是哪一个英雄”的场景。
    """
    if search_bgr is None or template_bgr is None:
        return -1.0

    sh, sw = search_bgr.shape[:2]
    th0, tw0 = template_bgr.shape[:2]
    if sh < 2 or sw < 2 or th0 < 2 or tw0 < 2:
        return -1.0

    best = -1.0
    for s in _iter_scales(HERO_TEMPLATE_SCALE_MIN, HERO_TEMPLATE_SCALE_MAX, HERO_TEMPLATE_SCALE_STEP):
        tw = int(round(tw0 * s))
        th = int(round(th0 * s))
        if tw < 2 or th < 2:
            continue
        if th > sh or tw > sw:
            continue

        tpl = cv2.resize(template_bgr, (tw, th), interpolation=cv2.INTER_AREA if s < 1.0 else cv2.INTER_CUBIC)
        res = cv2.matchTemplate(search_bgr, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        if max_val > best:
            best = float(max_val)

    return best


def _recognize_hero(card_roi):
    """
    识别卡片中的英雄 ID。
    在 card_roi 上半部分裁剪头像区域，与 HERO_TEMPLATES 做模板匹配。
    """
    if card_roi is None:
        return None

    h, w = card_roi.shape[:2]
    face_roi = card_roi[0:int(h * 0.6), 0:w]

    best_hero = None
    best_score = 0.0

    for hero_id, tpl_list in HERO_TEMPLATES.items():
        for tpl_path in tpl_list:
            if not os.path.exists(tpl_path):
                continue
            tpl = load_template(tpl_path)
            if tpl is None:
                continue

            max_val = _best_multiscale_match_score(face_roi, tpl)
            if max_val > best_score:
                best_score = max_val
                best_hero = hero_id

    # 调试：总是打印最佳匹配
    if best_hero:
        print(f"  最佳匹配: {best_hero} ({best_score:.3f})")
    else:
        print(f"  最佳匹配: None (最高分 {best_score:.3f})")

    # 不同英雄使用不同的匹配阈值
    if best_hero:
        hero_thresholds = {"gubian": 0.8, "dashu": 0.8, "luka": 0.8, "kaka": 0.9, "bailang": 0.8}
        required = hero_thresholds.get(best_hero, 0.6)
        if best_score > required:
            return best_hero

    return None
def has_fancy_border(card_roi,
                     border_thickness: int = 0,
                     empty_thresh: int = 0,
                     fancy_thresh: int = 0,
                     top_ratio: float = BORDER_TOP_RATIO):
    """
    利用已裁好的 card_roi 做“有花边 / 无花边”判断：
    - 只看最外圈若干像素（border_thickness）
    - 只统计边框“上方一定比例”的区域（top_ratio，例如 0.10 表示上方 10%）
    - 用 Canny 统计边缘数量
    - 边缘 < empty_thresh: 认为是空槽，无角色
    - empty_thresh ≤ 边缘 < fancy_thresh: 有角色但平框
    - 边缘 ≥ fancy_thresh: 有角色且有花边

    返回：
    - None: 空槽
    - True: 有花边
    - False: 平框
    """
    if card_roi is None:
        return False

    h, w = card_roi.shape[:2]
    gray = cv2.cvtColor(card_roi, cv2.COLOR_BGR2GRAY)

    t = border_thickness
    # 只保留“上方一定比例”范围内的边框像素，其他置 0
    outer = np.zeros_like(gray)

    # 上方统计范围：至少覆盖 t 行，避免 t>top_h 时上边框被截断
    top_ratio = float(top_ratio)
    if top_ratio <= 0:
        top_h = t
    else:
        top_h = max(t, int(round(h * min(top_ratio, 1.0))))

    # 在上方 top_h 行里，仅保留边框厚度 t 的区域（更聚焦“框”而不是头像内容）
    # 1) 顶边：0~t 行
    outer[0:min(t, top_h), :] = gray[0:min(t, top_h), :]
    # 2) 左右边：在 0~top_h 行范围内保留左右 t 列
    outer[0:top_h, 0:t] = gray[0:top_h, 0:t]
    outer[0:top_h, w - t:w] = gray[0:top_h, w - t:w]

    edges = cv2.Canny(outer, 50, 150)
    edge_count = int(np.count_nonzero(edges))
    print(f"边缘像素数: {edge_count}")

    if edge_count < empty_thresh:
        # 空槽，后续不再尝试识别英雄
        return None
    if edge_count >= fancy_thresh:
        return True
    return False


def _top_band_edge_count(card_roi, top_ratio: float = BORDER_TOP_RATIO) -> int:
    """只取最上方 top_ratio 条带做 Canny，返回 edge_count。"""
    if card_roi is None:
        return 0
    h, w = card_roi.shape[:2]
    if h <= 0 or w <= 0:
        return 0
    gray = cv2.cvtColor(card_roi, cv2.COLOR_BGR2GRAY)
    top_h = max(1, int(h * float(top_ratio)))
    top_band = gray[0:top_h, :]
    edges = cv2.Canny(top_band, 50, 150)
    return int(np.count_nonzero(edges))


def _save_heroes_to_txt(hero_dict):
    """
    将识别到的英雄练度信息写入文本文件。
    要求：
    - 文本文件里的“名字”直接用图片名（这里用 ALL_HERO_NAMES 里的基础名）；
    - 有花边记为“高”，无花边记为“低”；
    - 如果完全未识别到该角色，则练度标注为“未拥有”。
    """
    lines = []

    # 先把所有给定的角色都列出来，未识别则标记为“未拥有”
    for hero_name in ALL_HERO_NAMES:
        border_status = hero_dict.get(hero_name)
        if border_status is None:
            status_str = "未拥有"
        else:
            # border_status 目前为 "有花边" 或 "平框"
            if border_status == "有花边":
                status_str = "高"
            else:
                status_str = "低"
        lines.append(f"{hero_name},{status_str}")

    content = "\n".join(lines)
    with open(WAREHOUSE_TXT_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"已将 {len(lines)} 个英雄信息写入 {WAREHOUSE_TXT_PATH}")


def _recognize_grid_from_first_card(
    img,
    x0,
    y0,
    rows,
    cols,
    debug_label="",
    card_width=None,
    card_height=None,
    col_gap=None,
    row_gap=None,
    max_consecutive_unrecognized: Optional[int] = None,
):
    """
    从首个卡片左上角坐标 (x0, y0) 开始，按给定行数/列数遍历卡片。
    如果开启 DEBUG_SAVE_SLOTS，会把每个槽位的截图保存到 debug 目录，文件名包含 debug_label。
    返回：dict[hero_id] = border_status（"有花边" / "平框"），
    仓库不会有重复英雄时，以第一次为准。
    """
    heroes = {}
    debug = DEBUG_SAVE_SLOTS
    debug_dir = get_work_path("debug")
    if debug:
        os.makedirs(debug_dir, exist_ok=True)

    # 使用自定义或全局的卡片尺寸与间距
    cw = card_width if card_width is not None else CARD_WIDTH
    ch = card_height if card_height is not None else CARD_HEIGHT
    cg = col_gap if col_gap is not None else COL_GAP
    rg = row_gap if row_gap is not None else ROW_GAP

    vis = img.copy() if debug else None

    consecutive_unrecognized = 0

    for row in range(rows):
        for col in range(cols):
            card_roi = _extract_card_roi(img, row, col, x0, y0, cw, ch, cg, rg)
            if card_roi is None:
                continue

            if debug:
                fname = f"{debug_label}_r{row}_c{col}.png"
                cv2.imwrite(os.path.join(debug_dir, fname), card_roi)
                # 在可视化大图上画出预期的卡片矩形
                x = x0 + col * (cw + cg)
                y = y0 + row * (ch + rg)
                cv2.rectangle(vis, (x, y), (x + cw, y + ch), (0, 255, 0), 2)

            # 先识别英雄：识别不到就直接跳过（不做边框判定）
            hero_id = _recognize_hero(card_roi)
            if not hero_id:
                print(f"[{debug_label}] r{row} c{col}: 未识别英雄，跳过")
                consecutive_unrecognized += 1
                if (
                    max_consecutive_unrecognized is not None
                    and consecutive_unrecognized >= int(max_consecutive_unrecognized)
                ):
                    print(
                        f"[{debug_label}] 连续 {consecutive_unrecognized} 个未识别英雄，"
                        f"判定该分类下已无角色，提前结束本次读取。"
                    )
                    if debug and vis is not None:
                        big_name = f"{debug_label}_grid_overview.png"
                        cv2.imwrite(os.path.join(debug_dir, big_name), vis)
                    return heroes
                continue
            else:
                consecutive_unrecognized = 0

            # 再判定边框（只用上方 8% 条带；edge_count > 50 => 有边框）
            edge_count = _top_band_edge_count(card_roi, top_ratio=BORDER_TOP_RATIO)
            fancy = edge_count > int(BORDER_EDGE_THRESHOLD)
            fancy_str = "有花边" if fancy else "平框"
            print(f"  边框检测: edge_count={edge_count}, threshold={BORDER_EDGE_THRESHOLD}, 结果={fancy_str}")

            if hero_id in heroes:
                print(f"[{debug_label}] r{row} c{col}: {hero_id} 已记录过, 边框={fancy_str}")
                continue

            # heroes 字典只记录“有无花边”
            heroes[hero_id] = fancy_str

            # 每个卡槽输出：英雄 ID + 是否有花边
            print(
                f"[{debug_label}] r{row} c{col}: 英雄={hero_id}, 边框={fancy_str}"
            )

    if debug and vis is not None:
        big_name = f"{debug_label}_grid_overview.png"
        cv2.imwrite(os.path.join(debug_dir, big_name), vis)

    return heroes


def enter_warehouse_scrolled_view(max_retry: int = 2) -> bool:
    """
    从“英雄厅堂 -> 初始仓库界面”（只露出一行多）进入到
    “已向下拖动、能看到三行半角色”的稳定界面。

    利用那一行说明文字的纵坐标作为锚点：
    - 初始界面：说明文字在较上方（y_initial）
    - 成功拖动后：说明文字会落到较下方且位置稳定
    """
    for attempt in range(1, max_retry + 1):
        img1 = screenshot_bgr()
        anchor1 = _locate_scroll_anchor_y(img1)
        if not anchor1:
            print("未找到滚动锚点文字，大概率当前不在仓库界面。")
            return False

        x1, y1 = anchor1
        print(f"第 {attempt} 次尝试拖动前，锚点文字坐标: ({x1}, {y1})")

        ih, iw = img1.shape[:2]  # 截图尺寸 == 屏幕尺寸（pyautogui.screenshot）

        def _clamp(v: int, lo: int, hi: int) -> int:
            return max(lo, min(hi, int(v)))

        # 以 relevel 锚点本身作为拖动起点；坐标必须钳在屏幕内，否则鼠标会“飞”到边缘
        start_x = _clamp(x1, 5, iw - 5)
        start_y = _clamp(y1, 5, ih - 5)
        end_x = start_x
        # 按住往上拖：列表向下滚动（更符合“下移到三行半视图”的手势）
        end_y = _clamp(start_y - DRAG_DISTANCE, 5, ih - 5)

        print(f"发送拖动指令: ({start_x}, {start_y}) -> ({end_x}, {end_y})")

        send_drag(start_x, start_y, end_x, end_y)

        time.sleep(0.8)  # 等待 AHK 执行拖动 + 动画结束

        img2 = screenshot_bgr()
        anchor2 = _locate_scroll_anchor_y(img2)
        if not anchor2:
            print("拖动后未找到滚动锚点文字，重试。")
            continue

        x2, y2 = anchor2
        print(f"第 {attempt} 次拖动后，锚点文字坐标: ({x2}, {y2})")

        # 如果拖动成功，说明文字应明显下移；如果被弹回初始界面，则 y2 接近 y1
        if abs(y2 - y1) < 20:
            print("拖动距离可能不够，被弹回初始位置，准备重试。")
            continue

        print("检测到仓库已进入拖动后的稳定界面。")
        return True

    print("多次尝试拖动后仍未进入稳定界面。")
    return False


def recognize_hand_five(all_heroes: dict):
    """
    在拖动完成后的界面中，读取 rehand 下方的 5 个“共鸣之手”角色。
    识别结果写入 all_heroes（原地更新）。
    绿框与 rehand 红框左对齐，且位于红框下方。
    """
    img = screenshot_bgr()
    pos = _match_template_with_box(img, tpl_rehand, threshold=0.8)
    if not pos:
        print("未找到 rehand 锚点，跳过共鸣之手 5 个位置读取。")
        return

    ax, ay, tw, th = pos
    # 模板自身的左边界、下边界：绿框左边 = 红框左边，且绿框在红框下方
    anchor_left = ax - tw // 2
    anchor_bottom = ay + th // 2

    # 共鸣之手下方 5 个位置：
    # - X 起点：和 rehand 红框左边对齐（再做少量微调）；
    # - Y 起点：在 rehand 红框下边缘再向下移动一个红框高度（再做少量微调）。
    x0 = anchor_left + HAND_FIRST_OFFSET_X
    y0 = anchor_bottom + th + HAND_FIRST_OFFSET_Y-5
    print(
        f"rehand 锚点在 ({ax}, {ay})，模板左下角约为 ({anchor_left}, {anchor_bottom})，"
        f"估算首卡坐标 ({x0}, {y0})"
    )

    # 共鸣之手：取消绿框间隔，并在上一版基础上稍微放大宽高
    hand_card_width = int(CARD_WIDTH * 7.0 / 8.0 * 1.2* 1.2)
    hand_card_height = int(CARD_HEIGHT * 8.0 / 9.0 * 1.2* 1.2)
    hand_col_gap = 0

    heroes = _recognize_grid_from_first_card(
        img,
        x0,
        y0,
        rows=1,
        cols=5,
        debug_label="hand",
        card_width=hand_card_width,
        card_height=hand_card_height,
        col_gap=hand_col_gap,
        row_gap=ROW_GAP,
        max_consecutive_unrecognized=None,
    )
    all_heroes.update(heroes)


def recognize_knights_for_current_filter(all_heroes: dict):
    """
    在当前种族/职业筛选条件下，读取 reknight 下方的角色网格（最多 MAX_ROWS 行 × NUM_COLS）。
    识别结果写入 all_heroes（原地更新）。
    绿框与 reknight 红框左对齐，且位于红框下方。
    """
    img = screenshot_bgr()
    pos = _match_template_with_box(img, tpl_reknight, threshold=0.8)
    if not pos:
        print("未找到 reknight 锚点，本组合下可能没有共鸣骑士。")
        return

    ax, ay, tw, th = pos
    anchor_left = ax - tw // 2
    anchor_bottom = ay + th // 2

    # 共鸣骑士下方的网格：
    # - X 起点：和 reknight 红框左边对齐（再做少量微调）；
    # - Y 起点：在 reknight 红框下边缘再向下移动半个红框高度（再做少量微调）。
    x0 = anchor_left + KNIGHT_FIRST_OFFSET_X
    y0 = anchor_bottom + th // 2 + KNIGHT_FIRST_OFFSET_Y-5
    print(
        f"reknight 锚点在 ({ax}, {ay})，模板左下角约为 ({anchor_left}, {anchor_bottom})，"
        f"估算首卡坐标 ({x0}, {y0})"
    )

    # 共鸣骑士：取消绿框之间的水平间隔，并在上一版基础上略微调整宽度
    knight_card_width = int(CARD_WIDTH * 11.0 / 10.0 * 0.95)
    knight_card_height = int(CARD_HEIGHT * 1.15)
    heroes = _recognize_grid_from_first_card(
        img,
        x0,
        y0,
        rows=MAX_ROWS,
        cols=NUM_COLS,
        debug_label="knight",
        card_width=knight_card_width,
        card_height=CARD_HEIGHT,
        col_gap=0,
        row_gap=ROW_GAP,
        # 连续检测到两个未识别英雄，认为该筛选分类下已无角色，直接进入下一个分类
        max_consecutive_unrecognized=2,
    )
    all_heroes.update(heroes)


def scan_all_race_job_combinations():
    """
    整体流程：
    1. 点击 ck 进入仓库界面；
    2. 用 relevel 拖动到“三行半”稳定界面；
    3. 读取 rehand 下方 5 个角色；
    4. 点击 catalog 进入筛选界面；
    5. 按顺序遍历所有种族(yg..xk) × 职业(tk..zs)组合：
       - 先点种族，再点职业；
       - 用 reknight 锚点读取下方角色；
    6. 读取完成后点击 exit 退出；
    7. 将所有识别到的英雄写入文本文件。
    """
    # 初始化模板，自动从 templates 目录加载所有角色头像和练度花边
    init_templates_from_dir()

    all_heroes: dict = {}

    # 1. 点击 ck 进入仓库
    if not wait_and_click(tpl_ck, "ck(进入仓库)", 0.7):
        print("点击 ck 进入仓库失败。")
        return

    time.sleep(1.0)

    # 2. 拖动到三行半视图
    if not enter_warehouse_scrolled_view():
        print("进入三行半视图失败，终止扫描。")
        return

    # 3. 读取共鸣之手 5 个位置
    recognize_hand_five(all_heroes)

    # 4. 打开选择种族/职业界面
    if not wait_and_click(tpl_catalog, "catalog(打开筛选界面)", 0.8):
        print("点击 catalog 失败，无法进入筛选界面。")
        return

    time.sleep(1.0)

    race_order = ["yg", "ly", "mx", "wl", "bs", "em", "xk"]
    job_order = ["tk", "fz", "ss", "fs", "yx", "zs"]

    for race in race_order:
        tpl_race = RACE_TEMPLATES.get(race)
        if not tpl_race:
            print(f"未配置种族模板: {race}")
            continue

        if not wait_and_click(tpl_race, f"race_{race}", 0.8):
            print(f"点击种族 {race} 失败，跳过该种族。")
            continue

        time.sleep(0.5)

        for job in job_order:
            tpl_job = JOB_TEMPLATES.get(job)
            if not tpl_job:
                print(f"未配置职业模板: {job}")
                continue

            if not wait_and_click(tpl_job, f"job_{job}", 0.8):
                print(f"点击职业 {job} 失败，跳过该组合。")
                continue

            print(f"开始读取组合: 种族={race}, 职业={job}")
            time.sleep(0.8)  # 等待界面刷新

            recognize_knights_for_current_filter(all_heroes)

    # 6. 完成后退出
    if not wait_and_click(tpl_exit, "exit(退出仓库)", 0.8):
        print("点击 exit 退出仓库失败，请手动检查。")

    # 7. 保存结果
    _save_heroes_to_txt(all_heroes)


def main():
    """主函数，供其他脚本调用"""
    # 遍历所有种族/职业组合并识别英雄 + 练度
    scan_all_race_job_combinations()

if __name__ == "__main__":
    main()
