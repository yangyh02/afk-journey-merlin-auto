from common import wait_and_click, find_center, screenshot_bgr, get_template_path, get_work_path, load_template
from warehouse import (
    init_templates_from_dir,
    WAREHOUSE_TXT_PATH,
)
import cv2
import os
import time

# 静默版本的 find_center，不输出匹配得分
def find_center_silent(template_path, threshold=0.7, timeout=3.0):
    template = load_template(template_path)
    h, w = template.shape[:2]

    start_time = time.time()
    while time.time() - start_time < timeout:
        img = screenshot_bgr()
        res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val >= threshold:
            top_left = max_loc
            center_x = top_left[0] + w // 2
            center_y = top_left[1] + h // 2
            return center_x, center_y
        
        time.sleep(0.5)
    
    return None

# === 模板路径，对应你的文件名 ===
tpl_advance       = get_template_path("guajiguanqia.png")
tpl_wanfamulu     = get_template_path("wanfamulu.png")
tpl_huanlingcha   = get_template_path("tiaozhan.png")
tpl_autocha       = get_template_path("autocha.png")
tpl_fail          = get_template_path("fail.png")
tpl_repeat        = get_template_path("repeat.png")
tpl_lineup        = get_template_path("lineup.png")
tpl_artificial    = get_template_path("artificial.png")
tpl_right         = get_template_path("right.png")
tpl_oneclick      = get_template_path("oneclick.png")
tpl_exit          = get_template_path("exit.png")
tpl_end           = get_template_path("end.png")
tpl_not_owned     = get_template_path("not owned.png")
tpl_quxiao        = get_template_path("quxiao.png")

tpl_tiaozhanonly  = get_template_path("tiaozhanonly.png")

tpl_zidongtiaozhanzhong  = get_template_path("zidongtiaozhanzhong.png")

tpl_guajijixian   = get_template_path("guajijixian.png")
tpl_querengoumaimenpiao = get_template_path("querengoumaimenpiao.png")

tpl_huidaoguaji   = get_template_path("huidaoguaji.png")
tpl_tuichulibao   = get_template_path("tuichulibao.png")

# 推图模式配置：不同模式使用不同的入口模板
MODE_CONFIG = {
    "huanling": {
        "entry_templates": ["huanlingcha.png"],
    },
    "normal": {
        "entry_templates": ["tiaozhan.png", "tiaozhanonly.png"],
    },
}

# 一场战斗最长等待多久（秒）
MAX_BATTLE_TIME = 180

# ===== 阵容练度匹配相关配置 =====

# 视为"低/高/未拥有"的数值，用于比较"仓库练度 >= 阵容要求练度"
LEVEL_SCORE = {
    "未拥有": 0,
    "低": 1,
    "高": 2,
}

# 特殊标注角色：这些角色只要"拥有即可"（高/低都行），但不能是"未拥有"
# 直接填 warehouse_heroes.txt 里的名字（例如 "nvyao"）
SPECIAL_HERO_SET = {
    # 示例：在这里填你想放宽要求的角色
    # "nvyao",
    "meimo",
    "kululu",
    "shizi",
}

# 阵容界面 5 个头像的大致布局（相对于"一键采用"按钮）
# 你后续可以根据调试截图微调这些参数
LINEUP_CARD_WIDTH = 47
LINEUP_CARD_HEIGHT = 63
LINEUP_COL_GAP = 0

# 以一键采用按钮中心为参考点：
#   - X 起点 = btn_x - LINEUP_FIRST_OFFSET_X
#   - Y 起点 = btn_y - LINEUP_FIRST_OFFSET_Y
# （也就是头像区域大概在按钮上方一块区域）
LINEUP_FIRST_OFFSET_X = 200
LINEUP_FIRST_OFFSET_Y = 200

# 调试用整体偏移（像素）：正数表示向右/向下移动
# 参考：如果你想"向下 1 个框高"，就填 LINEUP_CARD_HEIGHT；"向右 1.3 个框宽"，就填 round(1.3 * LINEUP_CARD_WIDTH)
LINEUP_SHIFT_X_PX = int(round(1.6 * LINEUP_CARD_WIDTH))
LINEUP_SHIFT_Y_PX = int(round(0.75 * LINEUP_CARD_HEIGHT))

# 第二套布局：整体在 X 方向再额外平移的比例/像素
# 默认向左平移半个头像宽度，你可以调下面这两个变量：
LINEUP_SECOND_LAYOUT_SHIFT_X_FACTOR = -0.5
LINEUP_SECOND_LAYOUT_SHIFT_X_PX = int(round(LINEUP_SECOND_LAYOUT_SHIFT_X_FACTOR * LINEUP_CARD_WIDTH))

# 阵容界面头像明显比仓库里小，为了匹配稳定，
# 这里专门为阵容识别准备一套"更偏向缩小"的多尺度列表。
# 注意：这些只是模板缩放比例，不会改动截图本身。
LINEUP_TEMPLATE_SCALES = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

# 头像识别：多尺度模板匹配（解决不同分辨率/缩放导致头像大小不一致）
# - 你可以直接改这里的缩放范围与步进
LINEUP_HERO_TEMPLATE_SCALE_MIN = 0.40
LINEUP_HERO_TEMPLATE_SCALE_MAX = 0.80
LINEUP_HERO_TEMPLATE_SCALE_STEP = 0.05

# 英雄头像匹配阈值
LINEUP_HERO_MATCH_THRESHOLD = 0.6


# 调试截图输出目录
DEBUG_DIR = get_work_path("debug")

# Debug模式开关：True=开启调试功能（保存截图、打印调试信息），False=关闭调试功能
DEBUG_MODE = False

# 控制是否输出等待超时信息
PRINT_WAIT_TIMEOUT = False

# 阵容界面花边检测：只取头像框顶部多少比例作为检测条带
LINEUP_BORDER_TOP_RATIO = 0.08


def has_fancy_border_lineup(
    card_roi,
    top_ratio: float = LINEUP_BORDER_TOP_RATIO,
):
    """
    阵容界面专用的花边检测逻辑：
    - 只看卡片最上方 top_ratio（默认 10%）高度区域；
    - 对该条带做 Canny 边缘检测并统计边缘像素数；
    - 返回值 = 0: 没有花边；
    - 返回值 > 0: 有花边（边缘像素数）。

    返回 edge_count：
    - edge_count == 0: 没有花边
    - edge_count > 0: 有花边
    """
    if card_roi is None:
        return 0

    h, w = card_roi.shape[:2]
    if h <= 0 or w <= 0:
        return 0

    gray = cv2.cvtColor(card_roi, cv2.COLOR_BGR2GRAY)
    top_h = max(1, int(h * top_ratio))
    top_band = gray[0:top_h, :]

    edges = cv2.Canny(top_band, 50, 150)
    edge_count = int((edges > 0).sum())

    return edge_count


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
    只做评分，不返回位置；用于"选出是哪一个英雄"的场景。
    """
    if search_bgr is None or template_bgr is None:
        return -1.0

    sh, sw = search_bgr.shape[:2]
    th0, tw0 = template_bgr.shape[:2]
    if sh < 2 or sw < 2 or th0 < 2 or tw0 < 2:
        return -1.0

    best = -1.0
    for s in _iter_scales(LINEUP_HERO_TEMPLATE_SCALE_MIN, LINEUP_HERO_TEMPLATE_SCALE_MAX, LINEUP_HERO_TEMPLATE_SCALE_STEP):
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
    from warehouse import HERO_TEMPLATES
    
    if card_roi is None:
        return None

    h, w = card_roi.shape[:2]
    face_roi = card_roi[0:h, 0:w]

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

    # 不同英雄使用不同的匹配阈值
    if best_hero:
        if best_hero in ["gubian", "dashu", "luka"]:
            # gubian 和 dashu 要求准确率大于0.8
            if best_score > 0.8:
                print(f"识别到英雄 {best_hero}，相似度 {best_score:.3f}")
                return best_hero
        else:
            # 其他英雄使用0.75的阈值
            if best_score >= 0.75:
                print(f"识别到英雄 {best_hero}，相似度 {best_score:.3f}")
                return best_hero

    return None


def wait_for_appearance(template_path, name, threshold=0.8, timeout=MAX_BATTLE_TIME, interval=0.5):
    """循环等待某张图出现，出现返回坐标，超时返回 None。"""
    start = time.time()
    attempt = 0
    while True:
        attempt += 1
        pos = find_center_silent(template_path, threshold)
        if pos:
            if PRINT_WAIT_TIMEOUT:
                print(f"{name} 出现，第 {attempt} 次检测，坐标: {pos}")
            return pos

        elapsed = time.time() - start
        if elapsed > timeout:
            if PRINT_WAIT_TIMEOUT:
                print(f"{name} 在 {timeout} 秒内未出现，放弃等待。")
            return None

        if PRINT_WAIT_TIMEOUT:
            print(f"{name} 第 {attempt} 次未出现，{interval} 秒后重试（已等待 {elapsed:.1f} 秒）...")
        time.sleep(interval)


def wait_for_any(templates, threshold=0.8, timeout=MAX_BATTLE_TIME, interval=0.5):
    """
    循环等待多张图中的任意一张出现。

    templates: List[Tuple[template_path, name]]
    返回：
        - (template_path, name, pos) 命中
        - None 超时
    """
    start = time.time()
    attempt = 0
    while True:
        attempt += 1
        for template_path, name in templates:
            pos = find_center_silent(template_path, threshold)
            if pos:
                if PRINT_WAIT_TIMEOUT:
                    print(f"{name} 出现，第 {attempt} 次检测，坐标: {pos}")
                return template_path, name, pos

        elapsed = time.time() - start
        if elapsed > timeout:
            if PRINT_WAIT_TIMEOUT:
                names = " / ".join([n for _, n in templates])
                print(f"{names} 在 {timeout} 秒内未出现，放弃等待。")
            return None

        time.sleep(interval)


def _load_warehouse_levels():
    """
    读取仓库扫描结果文本，生成 {hero_name: level_str} 字典。
    文本每行格式为：名字,高/低/未拥有
    """
    hero_levels = {}
    if not os.path.exists(WAREHOUSE_TXT_PATH):
        print(f"未找到仓库练度文件：{WAREHOUSE_TXT_PATH}，将视为全部未拥有。")
        return hero_levels

    with open(WAREHOUSE_TXT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "," not in line:
                continue
            name, lvl = line.split(",", 1)
            hero_levels[name.strip()] = lvl.strip()
    print(f"已读取仓库练度信息，共 {len(hero_levels)} 条。")
    return hero_levels


def _capture_lineup_slots(debug_label="lineup", extra_shift_x_px: int = 0):
    """
    在"通关阵容界面"下：
    - 通过 oneclick(i) 按钮位置估算 5 个头像的大致区域；
    - 返回 [(card_roi, (x, y, w, h)), ...]；
    - 如果 DEBUG_MODE 为 True，同时输出一张画有绿框的调试大图到 DEBUG_DIR。
    """
    img = screenshot_bgr()
    pos_btn = find_center_silent(tpl_oneclick, threshold=0.8)
    if not pos_btn:
        print("未找到一键采用按钮，无法估算阵容 5 个头像位置。")
        return []

    btn_x, btn_y = pos_btn
    ih, iw = img.shape[:2]

    # 估算第一张头像左上角
    x0 = max(
        0,
        int(
            round(
                (btn_x - LINEUP_FIRST_OFFSET_X) + LINEUP_SHIFT_X_PX
            )
        ),
    ) + extra_shift_x_px
    y0 = max(
        0,
        int(
            round(
                (btn_y - LINEUP_FIRST_OFFSET_Y) + LINEUP_SHIFT_Y_PX
            )
        ),
    )

    slots = []
    vis = img.copy()

    for idx in range(5):
        x = x0 + idx * (LINEUP_CARD_WIDTH + LINEUP_COL_GAP)
        y = y0
        w = LINEUP_CARD_WIDTH
        h = LINEUP_CARD_HEIGHT

        if x < 0 or y < 0 or x + w > iw or y + h > ih:
            continue

        roi = img[y : y + h, x : x + w]
        slots.append((roi, (x, y, w, h)))
        cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 255, 0), 2)

    if DEBUG_MODE:
        os.makedirs(DEBUG_DIR, exist_ok=True)
        debug_path = os.path.join(
            DEBUG_DIR,
            f"{debug_label}_{int(time.time())}.png",
        )
        cv2.imwrite(debug_path, vis)
        print(f"阵容头像调试截图已保存：{debug_path}")

    return slots


def _recognize_lineup_with_levels():
    """
    识别当前通关阵容界面的 5 个角色及其"高/低/未拥有"：
    - 使用仓库里的头像识别逻辑 _recognize_hero；
    - 使用 has_fancy_border 判断是否有花边：有花边=高，无花边=低，空槽=未拥有。
    返回：
        lineup_heroes: List[(hero_name, need_level_str)]
        debug_path: 调试截图路径（可能为 None）
    """
    init_templates_from_dir()

    # 两套布局：第一套为默认位置，第二套整体再往左平移一段距离
    layouts = [
        ("layout1", 0),
        ("layout2", LINEUP_SECOND_LAYOUT_SHIFT_X_PX),
    ]

    best_lineup = []
    best_debug_path = None
    best_count = -1

    for layout_name, extra_shift in layouts:
        slots = _capture_lineup_slots(
            debug_label=f"lineup_debug_{layout_name}",
            extra_shift_x_px=extra_shift,
        )
        if not slots:
            continue

        lineup_heroes = []

        # 重新生成一张可视化图，包含识别结果文字
        img = screenshot_bgr()
        vis = img.copy()

        for idx, (roi, (x, y, w, h)) in enumerate(slots):
            edge_cnt = has_fancy_border_lineup(roi)
            need_level = "高" if edge_cnt > 0 else "低"

            # 阵容头像比仓库小一圈，使用仓库中定义的多尺度匹配逻辑
            hero_id = _recognize_hero(roi)
            if hero_id:
                lineup_heroes.append((hero_id, need_level))
                label = f"{hero_id}:{need_level}"
            else:
                label = f"未知:{need_level}"

            cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(
                vis,
                label,
                (x, max(0, y - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (0, 255, 0),
                1,
                cv2.LINE_AA,
            )

        recognized_count = len([h for h, lvl in lineup_heroes if h])

        debug_path = None
        if DEBUG_MODE:
            debug_path = os.path.join(
                DEBUG_DIR,
                f"lineup_recognized_{layout_name}_{int(time.time())}.png",
            )
            cv2.imwrite(debug_path, vis)
            print(f"[{layout_name}] 阵容识别结果截图已保存：{debug_path}")

        print(f"[{layout_name}] 当前阵容识别结果：")
        for hero_id, need_level in lineup_heroes:
            print(f"  - {hero_id}，需要练度：{need_level}")

        # 选择规则：
        # 1. 优先选择"识别到 5 个角色"的布局；
        # 2. 如果两套都不是 5 个，则保留识别数量更多的那套；
        # 3. 数量相同则保留先出现的（保持原有行为为主）。
        if recognized_count == 5:
            best_lineup = lineup_heroes
            best_debug_path = debug_path
            best_count = recognized_count
            # 已经满足"5 个角色全识别"，可以直接结束循环
            break

        if recognized_count > best_count:
            best_lineup = lineup_heroes
            best_debug_path = debug_path
            best_count = recognized_count

    return best_lineup, best_debug_path


def _is_lineup_acceptable(hero_levels, lineup_heroes):
    """
    根据仓库练度 hero_levels 和 当前阵容 lineup_heroes 判断是否可以采用：
    - 普通角色：自家练度 >= 阵容要求练度；
    - SPECIAL_HERO_SET 中的角色：只要不是"未拥有"即可（高/低都行）。
    """
    for hero_id, need_level in lineup_heroes:
        own_level = hero_levels.get(hero_id, "未拥有")

        # 特殊标注：只要拥有即可
        if hero_id in SPECIAL_HERO_SET:
            if own_level == "未拥有":
                print(f"[阵容拒绝] 特殊角色 {hero_id} 未拥有。")
                return False
            print(f"[阵容通过] 特殊角色 {hero_id} 拥有（{own_level}），忽略需求 {need_level}。")
            continue

        own_score = LEVEL_SCORE.get(own_level, 0)
        need_score = LEVEL_SCORE.get(need_level, 1)  # 未能识别需求时，默认按"低"处理

        if own_score < need_score:
            print(
                f"[阵容拒绝] 角色 {hero_id} 自家练度={own_level}({own_score}) "
                f"< 需求练度={need_level}({need_score})"
            )
            return False

        print(
            f"[阵容通过] 角色 {hero_id} 自家练度={own_level}({own_score}) "
            f">= 需求练度={need_level}({need_score})"
        )

    return True


def debug_lineup_recognition():
    """
    调试函数（仅阵容识别，不参与推图流程）：
    - 请手动停留在"查看通关阵容界面"；
    - 直接运行本脚本，将：
        * 估算 5 个阵容头像框的位置并画绿框截一张调试大图；
        * 对每个槽位调用 has_fancy_border + _recognize_hero；
        * 在控制台打印「槽位索引 / 英雄 ID / 花边状态 / 边缘像素数」。
    """
    init_templates_from_dir()

    layouts = [
        ("layout1", 0),
        ("layout2", LINEUP_SECOND_LAYOUT_SHIFT_X_PX),
    ]

    for layout_name, extra_shift in layouts:
        slots = _capture_lineup_slots(
            debug_label=f"lineup_debug_{layout_name}",
            extra_shift_x_px=extra_shift,
        )
        if not slots:
            print(f"[{layout_name}] 未能获取到阵容头像槽位，确认是否已经在阵容界面。")
            continue

        print(f"--------- {layout_name} 阵容头像调试结果（索引 / 英雄ID / 花边状态 / 边缘像素数）---------")
        for idx, (roi, (x, y, w, h)) in enumerate(slots):
            edge_cnt = has_fancy_border_lineup(roi)
            border_str = "有花边" if edge_cnt > 0 else "无花边"

            # 使用仓库中定义的多尺度匹配逻辑
            hero_id = _recognize_hero(roi)
            hero_str = hero_id if hero_id else "未识别"
            print(f"[{idx}] 英雄={hero_str}，边框={border_str}，边缘像素数={edge_cnt}")

    print("如需查看框位置，请打开 debug 目录中的 lineup_debug_layout*_*.png 截图。")


def _try_detect_and_click_entry(entry_templates, timeout=3):
    """检测入口模板列表中的任意一个，检测到后点击。返回 True 表示成功。"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        for tpl_name in entry_templates:
            tpl_path = get_template_path(tpl_name)
            if find_center_silent(tpl_path, threshold=0.8):
                print(f"检测到 {tpl_name}，点击进入")
                if not wait_and_click(tpl_path, tpl_name, 0.8):
                    print(f"点击 {tpl_name} 失败")
                    return False
                return True
        time.sleep(0.5)
    return False


# ===== 推图状态机 =====
# 把原来"一个大 while + 多个标志位"的推图流程改成显式状态机：
# - 每个状态只做一件事，结束后显式返回下一个状态；
# - 所有内部循环都有上限（阵容扫描套数、状态切换次数、战斗等待时间），不会死循环；
# - 每次切换都打印日志，出问题时能直接看出卡在哪个状态、哪一步。

STATE_ENTER = "enter"                    # 进入推图玩法
STATE_LIMIT = "limit"                    # 处理挂机极限/购买门票弹窗
STATE_NEED_ENTRY = "need_entry"          # 重新点模式入口（end(k) 后）
STATE_START_BATTLE = "start_battle"      # 点击自动挑战
STATE_MONITOR_BATTLE = "monitor_battle"  # 监控战斗结果
STATE_ON_END = "on_end"                  # 处理 end(k)
STATE_ON_FAIL = "on_fail"                # 处理 fail(d)
STATE_LINEUP_OPEN = "lineup_open"        # 打开通关阵容界面
STATE_LINEUP_SELECT = "lineup_select"    # 在阵容界面挑选
STATE_EXIT = "exit"                      # 退出推图
STATE_DONE = "done"                      # 流程结束

# 单次进入阵容界面最多检查的阵容套数（防止阵容列表无限循环滚动导致死循环）
MAX_LINEUP_SCAN = 30
RIGHT_RETRY_COUNT = 3
RIGHT_RETRY_TIMEOUT = 1.0

# 整个推图流程最多允许的状态切换次数（安全阀）
MAX_TRANSITIONS = 500


class PushFlow:
    """推图流程状态机。run() 返回 True=正常结束（战斗超时无法判断），False=流程结束。"""

    def __init__(self, mode="normal", skip_manual=True, retry_count=3):
        self.mode = mode
        self.entry_templates = MODE_CONFIG[mode]["entry_templates"]
        self.mode_label = "幻灵推图" if mode == "huanling" else "推图"
        self.skip_manual = skip_manual
        self.retry_count = retry_count

        self.state = STATE_ENTER
        self.transitions = 0
        self.finished_ok = False

        # 推图进度数据
        self.have_lineup = False
        self.lineup_index = -1
        self.lineup_fail = 0
        self.lineup_start = 0

        self._handlers = {
            STATE_ENTER: self._st_enter,
            STATE_LIMIT: self._st_limit,
            STATE_NEED_ENTRY: self._st_need_entry,
            STATE_START_BATTLE: self._st_start_battle,
            STATE_MONITOR_BATTLE: self._st_monitor_battle,
            STATE_ON_END: self._st_on_end,
            STATE_ON_FAIL: self._st_on_fail,
            STATE_LINEUP_OPEN: self._st_lineup_open,
            STATE_LINEUP_SELECT: self._st_lineup_select,
            STATE_EXIT: self._st_exit,
        }

    def _done(self, ok):
        """标记最终结果并进入结束状态。"""
        self.finished_ok = ok
        return STATE_DONE

    def run(self):
        print(f"===== {self.mode_label} 状态机开始 =====")
        while self.state != STATE_DONE:
            if self.transitions >= MAX_TRANSITIONS:
                print(f"状态切换超过 {MAX_TRANSITIONS} 次，触发安全阀，结束流程。")
                self.finished_ok = False
                break

            handler = self._handlers.get(self.state)
            if handler is None:
                print(f"未知状态 {self.state}，结束流程。")
                self.finished_ok = False
                break

            prev_state = self.state
            next_state = handler()
            if next_state is None:
                print(f"状态 {prev_state} 未返回下一状态，结束流程。")
                self.finished_ok = False
                break

            self.state = next_state
            self.transitions += 1
            print(f"[状态机] {prev_state} -> {next_state}")

        print(f"===== {self.mode_label} 状态机结束（正常退出={self.finished_ok}）=====")
        return self.finished_ok

    # ---------- 各状态处理 ----------

    def _wait_for_any_state(self, candidates, timeout=10.0, interval=0.25, allow_gift_recovery=True):
        """等待目标状态模板出现，返回命中的模板路径；超时返回 None。"""
        deadline = time.time() + timeout
        missed_rounds = 0
        while time.time() < deadline:
            # 一轮必须完整检查所有候选模板；只有全部未命中才算一次未命中。
            for template_path, threshold in candidates:
                if find_center_silent(template_path, threshold=threshold, timeout=0.25):
                    return template_path

            missed_rounds += 1
            if allow_gift_recovery and missed_rounds >= 3:
                missed_rounds = 0
                if find_center_silent(tpl_tuichulibao, threshold=0.8, timeout=0.5):
                    print("连续 3 轮未识别到目标状态，检测到礼包界面，尝试点击 tuichulibao...")
                    if wait_and_click(tpl_tuichulibao, "tuichulibao", 0.8, timeout=3.0):
                        time.sleep(0.5)
                        continue

            time.sleep(interval)
        return None

    def _wait_for_entry(self, timeout=10.0):
        """等待当前模式入口出现；普通推图允许两个入口模板。"""
        return self._wait_for_any_state(
            [(get_template_path(name), 0.8) for name in self.entry_templates],
            timeout=timeout,
        )

    def _wait_after_action(self, candidates, action_name, timeout=10.0):
        """动作发送后必须看到目标模板，确认界面真的切换。"""
        hit = self._wait_for_any_state(candidates, timeout=timeout)
        if hit:
            print(f"{action_name} 后确认目标状态: {os.path.basename(hit)}")
        else:
            print(f"{action_name} 后未确认目标状态。")
        return hit

    def _st_enter(self):
        """进入推图玩法：wanfamulu -> advance -> 模式入口。"""
        if not wait_and_click(tpl_wanfamulu, "wanfamulu", 0.7):
            print("点击 wanfamulu 进入玩法目录失败。")
            return self._done(False)
        if not self._wait_after_action(
            [(tpl_advance, 0.8)], "wanfamulu", timeout=8.0
        ):
            return self._done(False)
        if not wait_and_click(tpl_advance, "advance(a)", 0.8):
            print("点击 advance(a) 进入推图失败。")
            return self._done(False)

        print(f"等待 {self.mode_label} 入口...")
        entry_path = self._wait_for_entry(timeout=10.0)
        if not entry_path:
            names = " / ".join(self.entry_templates)
            print(f"未检测到 {names}，点击 exit 退出")
            wait_and_click(tpl_exit, "exit(j)", 0.8)
            return self._done(False)

        if not wait_and_click(entry_path, os.path.basename(entry_path), 0.8):
            return self._done(False)
        next_path = self._wait_after_action(
            [(tpl_guajijixian, 0.7), (tpl_autocha, 0.8)],
            f"{os.path.basename(entry_path)}",
            timeout=10.0,
        )
        if not next_path:
            return self._done(False)

        print(f"进入 {self.mode_label} 成功")
        return STATE_LIMIT if next_path == tpl_guajijixian else STATE_START_BATTLE

    def _st_limit(self):
        """检查挂机极限弹窗，出现则点击购买门票确认。"""
        if find_center_silent(tpl_guajijixian, threshold=0.7, timeout=0.5):
            print("检测到 guajijixian，点击 querengoumaimenpiao...")
            if not wait_and_click(tpl_querengoumaimenpiao, "querengoumaimenpiao", 0.7):
                return self._done(False)
            if not self._wait_after_action(
                [(tpl_autocha, 0.8)], "querengoumaimenpiao", timeout=10.0
            ):
                return self._done(False)
        elif not find_center_silent(tpl_autocha, threshold=0.8, timeout=0.5):
            print("limit 状态既没有弹窗也没有 autocha，无法确认界面。")
            return self._done(False)
        return STATE_START_BATTLE

    def _st_need_entry(self):
        """end(k) 后回到玩法界面，需要重新点击模式入口。"""
        entry_path = self._wait_for_entry(timeout=10.0)
        if not entry_path:
            names = " / ".join(self.entry_templates)
            print(f"未检测到 {names}，退出推图")
            return self._done(False)
        if not wait_and_click(entry_path, os.path.basename(entry_path), 0.8):
            return self._done(False)
        next_path = self._wait_after_action(
            [(tpl_guajijixian, 0.7), (tpl_autocha, 0.8)],
            f"{os.path.basename(entry_path)}",
            timeout=10.0,
        )
        if not next_path:
            return self._done(False)
        return STATE_LIMIT if next_path == tpl_guajijixian else STATE_START_BATTLE

    def _st_start_battle(self):
        if not wait_and_click(tpl_autocha, "autocha(c)", 0.8):
            print("未找到 autocha(c)，推图流程结束。")
            return self._done(False)
        next_path = self._wait_after_action(
            [(tpl_fail, 0.8), (tpl_end, 0.8), (tpl_zidongtiaozhanzhong, 0.8)],
            "autocha(c)",
            timeout=12.0,
        )
        if next_path == tpl_fail:
            return STATE_ON_FAIL
        if next_path == tpl_end:
            return STATE_ON_END
        if next_path == tpl_zidongtiaozhanzhong:
            return STATE_MONITOR_BATTLE
        return self._done(False)

    def _st_monitor_battle(self):
        """
        监控战斗结果：
        - fail(d)：当前关卡失败；
        - end(k)：通过若干关卡后失败；
        - 只要定期看到 zidongtiaozhanzhong，就认为还在正常推图；
        - 超过 5 秒没看到时尝试处理误触弹窗（huidaoguaji）；
        - 3 分钟都没有任何标志时判定"无法判断"，结束流程。
        """
        last_seen_zidong = time.time()
        while True:
            # 结果模板优先于战斗中模板，避免结果页被误判为仍在战斗。
            if find_center_silent(tpl_fail, threshold=0.8, timeout=0.25):
                return STATE_ON_FAIL
            if find_center_silent(tpl_end, threshold=0.8, timeout=0.25):
                return STATE_ON_END
            if find_center_silent(tpl_zidongtiaozhanzhong, threshold=0.8, timeout=0.25):
                last_seen_zidong = time.time()
                time.sleep(0.25)
                continue

            now = time.time()
            if (now - last_seen_zidong) > 5:
                if find_center_silent(tpl_tuichulibao, threshold=0.8, timeout=0.5):
                    print("战斗状态丢失且检测到礼包界面，尝试点击 tuichulibao...")
                    if wait_and_click(tpl_tuichulibao, "tuichulibao", 0.8, timeout=3.0):
                        last_seen_zidong = time.time()
                        continue
                print("超过 5 秒未检测到 zidongtiaozhanzhong，尝试识别 huidaoguaji...")
                # 只等 1 秒识别 huidaoguaji，因为 5 秒未检测到 zidongtiaozhanzhong 本身就是在给 huidaoguaji 留加载时间
                if wait_and_click(tpl_huidaoguaji, "huidaoguaji", 0.8, timeout=1.0):
                    print("点击 huidaoguaji 成功，重新确认战斗状态...")
                    last_seen_zidong = time.time()
                    continue

            if (now - last_seen_zidong) > 180:
                print(
                    "超过 3 分钟未检测到自动挑战中、失败或结束模板，"
                    "无法确认战斗状态，按失败处理。"
                )
                return self._done(False)
            time.sleep(0.25)

    def _st_on_end(self):
        """end(k)：通过一段关卡后失败，重置阵容状态并重新进入模式。"""
        # end(k) 表示已经成功推进过，下一次应从第一套阵容重新开始。
        self.lineup_fail = 0
        self.lineup_index = -1
        self.have_lineup = False
        self.lineup_start = 0
        print("检测到 end(k)：推图成功，重置阵容编号和失败次数，重新进入模式1。")
        if not wait_and_click(tpl_end, "end(k)_click", 0.8):
            print("点击 end(k) 失败，退出推图。")
            return self._done(False)
        if not self._wait_for_entry(timeout=10.0):
            print("点击 end(k) 后未确认返回模式入口。")
            return self._done(False)
        return STATE_NEED_ENTRY

    def _st_on_fail(self):
        """fail(d)：点击 repeat 回到推图界面，然后决定阵容策略。"""
        if not wait_and_click(tpl_repeat, "repeat(e)", 0.8):
            print("点击 repeat(e) 失败，退出推图。")
            return self._done(False)

        post_repeat = self._wait_for_any_state(
            [
                (tpl_autocha, 0.8),
                (tpl_oneclick, 0.8),
                (tpl_right, 0.8),
                (tpl_artificial, 0.8),
                (tpl_lineup, 0.8),
            ],
            timeout=10.0,
        )
        if not post_repeat:
            print("点击 repeat(e) 后未确认返回推图或阵容界面。")
            return self._done(False)
        if post_repeat == tpl_autocha:
            return STATE_START_BATTLE

        if not self.have_lineup:
            # 第一次失败：进入阵容界面，从 0 开始选
            self.lineup_start = 0
            return STATE_LINEUP_OPEN

        self.lineup_fail += 1
        print(f"当前阵容 {self.lineup_index} 连续失败次数: {self.lineup_fail}")
        if self.lineup_fail < self.retry_count:
            # 还没到重试上限，继续用当前阵容
            return STATE_START_BATTLE

        # 同一阵容失败达到上限：从下一套开始找
        self.lineup_start = self.lineup_index + 1
        return STATE_LINEUP_OPEN

    def _st_lineup_open(self):
        # repeat 后可能已经在阵容界面；只有仍看到 lineup 按钮时才点击。
        if find_center_silent(tpl_oneclick, threshold=0.8, timeout=0.5) or find_center_silent(tpl_right, threshold=0.8, timeout=0.5):
            return STATE_LINEUP_SELECT
        if not wait_and_click(tpl_lineup, "lineup(f)", 0.8):
            print("点击 lineup(f) 进入通关阵容界面失败。")
            return self._done(False)
        if not self._wait_after_action(
            [(tpl_oneclick, 0.8), (tpl_right, 0.8), (tpl_artificial, 0.8)],
            "lineup(f)",
            timeout=10.0,
        ):
            return self._done(False)
        return STATE_LINEUP_SELECT

    def _click_next_lineup(self, action_name):
        """连续三次短等待识别 right，全部失败才判定没有下一套阵容。"""
        for attempt in range(1, RIGHT_RETRY_COUNT + 1):
            if wait_and_click(
                tpl_right,
                f"{action_name}（第 {attempt}/{RIGHT_RETRY_COUNT} 次）",
                0.8,
                timeout=RIGHT_RETRY_TIMEOUT,
            ):
                return True
        print("连续 3 次未找到 right.png，判定阵容已经用完。")
        return False

    def _st_lineup_select(self):
        """在阵容界面从 self.lineup_start 开始往后找可用阵容。"""
        current = 0
        if self.lineup_start > 0:
            print(f"进入阵容界面，先向右点击 {self.lineup_start} 次，跳过已经用过的阵容。")
        else:
            print("进入阵容界面，先向右点击 0 次，跳过已经用过的阵容。")

        while current < self.lineup_start:
            if not self._click_next_lineup(f"right(h) 跳过阵容 {current}"):
                # 还没跳够 start_index 次就已经点不到 right，说明本来阵容数就没那么多
                print("阵容数量不足以跳到指定起点，采用当前可见阵容并视为无更多阵容。")
                wait_and_click(tpl_oneclick, "oneclick(i_at_end)", 0.8)
                return STATE_EXIT
            current += 1
            time.sleep(0.5)

        scans = 0
        while scans < MAX_LINEUP_SCAN:
            scans += 1
            if self.skip_manual:
                print(f"检查阵容编号 {current} 是否含有手动战斗标志 g。")
                pos_g = find_center_silent(tpl_artificial, threshold=0.8)
            else:
                pos_g = None

            if not pos_g:
                hero_levels = _load_warehouse_levels()
                lineup_heroes, _debug_path = _recognize_lineup_with_levels()
                if _is_lineup_acceptable(hero_levels, lineup_heroes):
                    if not wait_and_click(tpl_oneclick, f"oneclick(i) 采用阵容 {current}", 0.8):
                        return STATE_EXIT

                    # 点击一键采用后，必须确认进入推图界面或出现未拥有提示。
                    post_adopt = self._wait_for_any_state(
                        [(tpl_not_owned, 0.8), (tpl_autocha, 0.8)],
                        timeout=10.0,
                    )
                    if post_adopt == tpl_not_owned:
                        print(f"阵容 {current} 检测到未拥有标志，点击取消并跳过。")
                        if not wait_and_click(tpl_quxiao, "quxiao(m) 取消当前阵容", 0.8):
                            print("点击取消失败，跳过当前阵容。")
                        time.sleep(1.0)
                        print(f"阵容 {current} 不可用，尝试切到下一套。")
                        if not self._click_next_lineup(f"right(h) 从阵容 {current} 切到下一套"):
                            # 点不到 right 说明已经是最后一套
                            print("已经是最后一套阵容，且检测到未拥有标志，仍然采用当前阵容后结束。")
                            wait_and_click(tpl_oneclick, "oneclick(i_last)", 0.8)
                            return STATE_EXIT
                        current += 1
                        time.sleep(0.5)
                        continue

                    if post_adopt != tpl_autocha:
                        print("点击 oneclick 后未确认进入推图界面。")
                        return self._done(False)

                    # 没有检测到 not owned.png，正常采用该阵容
                    print(f"采用当前阵容，编号为 {current}。")
                    self.have_lineup = True
                    self.lineup_index = current
                    self.lineup_fail = 0
                    return STATE_START_BATTLE

                print(f"阵容 {current} 练度不足，尝试切到下一套。")

            print(f"阵容 {current} 含 g 或练度不满足，尝试点击 right(h) 切到下一套。")
            if not self._click_next_lineup(f"right(h) 从阵容 {current} 切到下一套"):
                # 点不到 right 说明已经是最后一套
                print("已经是最后一套阵容，且含 g，仍然采用当前阵容后结束。")
                wait_and_click(tpl_oneclick, "oneclick(i_last)", 0.8)
                return STATE_EXIT

            current += 1
            time.sleep(0.5)

        print(f"已连续检查 {MAX_LINEUP_SCAN} 套阵容仍未找到可用阵容，安全退出。")
        return STATE_EXIT

    def _st_exit(self):
        """阵容用尽或流程结束：点击 exit 退出推图。"""
        print("没有更多可选阵容，退出推图。")
        wait_and_click(tpl_exit, "exit(j)", 0.8)
        time.sleep(1.0)
        wait_and_click(tpl_exit, "exit(j)", 0.8)
        return self._done(False)


def flow_push_mode1(mode="normal", skip_manual=True, retry_count=3):
    """
    推图主流程（状态机实现）。

    mode: "normal"（普通推图）或 "huanling"（幻灵推图）
    skip_manual: 是否跳过含手动战斗标志的阵容
    retry_count: 同一阵容连续失败多少次后换阵容（1-3）
    """
    init_templates_from_dir()
    flow = PushFlow(mode=mode, skip_manual=skip_manual, retry_count=retry_count)
    return flow.run()


def main(skip_manual=True, retry_count=3):
    """主函数，供其他脚本调用"""
    if DEBUG_MODE:
        debug_lineup_recognition()
        return True
    else:
        return flow_push_mode1(mode="normal", skip_manual=skip_manual, retry_count=retry_count)

if __name__ == "__main__":
    main()
