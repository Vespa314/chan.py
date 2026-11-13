"""
A股缠论买点扫描器 - Powered by chan.py

功能说明:
    - 批量扫描A股市场，自动识别近期出现买点的股票
    - 支持单只股票的缠论分析和图表展示
    - 一键复制买点股票列表中的全部代码，每行一个
    - 可视化显示K线、笔、线段、中枢、买卖点、MACD等

数据来源:
    - 使用 akshare 获取A股实时行情和历史K线数据

过滤规则:
    - 剔除ST股票、科创板(688)、北交所、B股
    - 剔除停牌股票和新股

依赖:
    - PyQt6: GUI框架
    - matplotlib: 图表绑定
    - akshare: A股数据接口
    - chan.py: 缠论分析核心库

使用方法:
    python App/ashare_bsp_scanner_gui.py
"""
import sys
from pathlib import Path

# 将项目根目录加入路径，以便导入 chan.py 核心模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox, QGroupBox,
    QMessageBox, QStatusBar, QSplitter, QTableWidget, QTableWidgetItem,
    QProgressBar, QHeaderView, QTextEdit
)
from PyQt6.QtCore import QDate, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPalette

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

import akshare as ak
import pandas as pd

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE


def apply_theme(app):
    """固定浅色调色板，避免系统深色模式与白色行情图混用。"""
    app.setStyle('Fusion')
    palette = QPalette()
    colors = {
        'Window': '#f3f6fa', 'WindowText': '#243247',
        'Base': '#ffffff', 'AlternateBase': '#f5f8fc',
        'Text': '#243247', 'Button': '#ffffff', 'ButtonText': '#243247',
        'Highlight': '#dbeafe', 'HighlightedText': '#173d75',
        'ToolTipBase': '#ffffff', 'ToolTipText': '#243247',
        'PlaceholderText': '#69788c', 'Link': '#2563eb',
        'Light': '#ffffff', 'Midlight': '#edf2f7',
        'Mid': '#cbd5e1', 'Dark': '#64748b', 'Shadow': '#94a3b8',
    }
    for role, color in colors.items():
        palette.setColor(getattr(QPalette.ColorRole, role), QColor(color))
    for role in ('WindowText', 'Text', 'ButtonText'):
        palette.setColor(QPalette.ColorGroup.Disabled,
                         getattr(QPalette.ColorRole, role), QColor('#69788c'))
    app.setPalette(palette)
    app.setStyleSheet("""
        QWidget { font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI";
                  font-size: 13px; }
        QGroupBox { background: #ffffff; border: 1px solid #dce3ed;
                    border-radius: 8px; margin-top: 12px; padding: 14px 10px 10px; }
        QGroupBox::title { subcontrol-origin: margin; left: 12px;
                          padding: 0 5px; color: #334155; font-weight: bold; }
        QPushButton { background: #ffffff; color: #334155; border: 1px solid #cbd5e1;
                      border-radius: 5px; padding: 7px 12px; }
        QPushButton:hover { background: #eff6ff; border-color: #93b4e8; }
        QPushButton:pressed { background: #dbeafe; }
        QPushButton#scanButton { background: #2563eb; color: #ffffff;
                                border-color: #2563eb; font-weight: bold; padding: 10px; }
        QPushButton#scanButton:hover { background: #1d4ed8; }
        QPushButton#scanButton:pressed { background: #1e40af; }
        QPushButton#stopButton { background: #fff1f2; color: #b42335;
                                border-color: #f2b8c0; padding: 10px; }
        QPushButton#stopButton:hover { background: #ffe4e6; }
        QPushButton#stopButton:pressed { background: #fecdd3; }
        QPushButton:disabled, QPushButton#scanButton:disabled,
        QPushButton#stopButton:disabled { background: #edf1f6; color: #69788c;
                                         border-color: #dce3ed; }
        QPushButton:focus, QToolButton:focus { border: 1px solid #2563eb; }
        QLineEdit, QTextEdit, QTableWidget { background: #ffffff; color: #243247;
            border: 1px solid #dce3ed; border-radius: 5px;
            selection-background-color: #dbeafe; selection-color: #173d75; }
        QLineEdit { padding: 7px; }
        QLineEdit:focus, QTextEdit:focus, QTableWidget:focus { border-color: #2563eb; }
        QLineEdit:disabled { background: #edf1f6; color: #69788c; }
        QTableWidget { alternate-background-color: #f5f8fc; gridline-color: #edf1f6; }
        QTableWidget::item { padding: 4px; }
        QTableWidget::item:selected { background: #dbeafe; color: #173d75; }
        QHeaderView::section { background: #edf2f8; color: #475569;
                              border: none; border-bottom: 1px solid #dce3ed; padding: 8px 4px; }
        QTableCornerButton::section { background: #edf2f8; border: none; }
        QCheckBox { spacing: 6px; padding: 3px 0; }
        QProgressBar { border: 1px solid #dce3ed; border-radius: 5px;
                       background: #edf2f8; color: #243247; text-align: center; min-height: 20px; }
        QProgressBar::chunk { background: #93baf5; border-radius: 4px; }
        QToolBar { background: #ffffff; border: none; spacing: 3px; padding: 4px; }
        QToolButton { background: transparent; color: #334155; border: 1px solid transparent;
                      border-radius: 4px; padding: 4px; }
        QToolButton:hover, QToolButton:checked { background: #dbeafe; }
        QSplitter::handle { background: #e2e8f0; }
        QStatusBar { background: #eaf0f7; color: #475569; }
        QStatusBar::item { border: none; }
        QToolTip { background: #ffffff; color: #243247; border: 1px solid #cbd5e1; padding: 5px; }
    """)


def style_chart(figure):
    """仅统一图表底色和坐标文字，保留涨跌及缠论图层的语义颜色。"""
    figure.set_facecolor('#ffffff')
    for ax in figure.axes:
        ax.set_facecolor('#ffffff')
        ax.tick_params(colors='#64748b')
        for spine in ax.spines.values():
            spine.set_color('#cbd5e1')
        for label in (ax.title, ax.xaxis.label, ax.yaxis.label):
            label.set_color('#334155')


def get_tradable_stocks():
    """
    获取所有可交易的A股股票列表

    过滤条件:
        1. 剔除ST股票（名称包含ST）
        2. 剔除科创板（688开头）
        3. 剔除北交所（8开头、43开头）
        4. 剔除B股（200开头深圳B股、900开头上海B股）
        5. 剔除存托凭证CDR（920开头）
        6. 剔除停牌股票（成交量为0）
        7. 剔除异常股票（最新价<=0）

    Returns:
        pd.DataFrame: 包含 ['代码', '名称', '最新价', '涨跌幅'] 列的股票列表
                      获取失败时返回空 DataFrame
    """
    try:
        # 获取A股实时行情
        df = ak.stock_zh_a_spot_em()

        # 过滤条件
        # 1. 剔除ST股票（名称包含ST）
        df = df[~df['名称'].str.contains('ST', case=False, na=False)]

        # 2. 剔除科创板（688开头）
        df = df[~df['代码'].str.startswith('688')]

        # 3. 剔除北交所（8开头，以43、83、87开头的也是北交所）
        df = df[~df['代码'].str.startswith('8')]
        df = df[~df['代码'].str.startswith('43')]

        # 4. 剔除B股（200开头深圳B股，900开头上海B股）
        df = df[~df['代码'].str.startswith('200')]
        df = df[~df['代码'].str.startswith('900')]

        # 5. 剔除存托凭证CDR（920开头）
        df = df[~df['代码'].str.startswith('920')]

        # 6. 剔除停牌股票（成交量为0或涨跌幅为空）
        df = df[df['成交量'] > 0]

        # 7. 剔除新股（上市不足60天的，这里简化处理，只保留有数据的）
        df = df[df['最新价'] > 0]

        return df[['代码', '名称', '最新价', '涨跌幅']].reset_index(drop=True)
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return pd.DataFrame()


class ScanThread(QThread):
    """
    批量扫描股票的后台线程

    在独立线程中遍历股票列表，对每只股票进行缠论分析，
    检测最近3天内是否出现买点。

    Signals:
        progress: (int, int, str) 当前进度、总数、当前股票信息
        found_signal: (dict) 发现买点时发出，包含股票详情和 CChan 对象
        finished: QThread 原生完成信号，统计保存在 success_count / fail_count
        log_signal: (str) 日志消息
    """
    progress = pyqtSignal(int, int, str)
    found_signal = pyqtSignal(dict)
    error = pyqtSignal(str)
    log_signal = pyqtSignal(str)

    def __init__(self, stock_list, config, days=365):
        """
        初始化扫描线程

        Args:
            stock_list: pd.DataFrame, 待扫描的股票列表
            config: CChanConfig, 缠论配置
            days: int, 获取多少天的历史数据，默认365天
        """
        super().__init__()
        self.stock_list = stock_list
        self.config = config
        self.days = days
        self.success_count = 0
        self.fail_count = 0
        self.cancelled = False

    def stop(self):
        """停止扫描，设置标志位让 run() 循环退出"""
        self.cancelled = True
        self.requestInterruption()

    def run(self):
        """
        线程主函数，遍历股票列表进行缠论分析

        扫描逻辑:
            1. 跳过无K线数据的股票
            2. 跳过停牌超过15天的股票
            3. 检测最近3天内是否出现买点
            4. 发现买点时通过 found_signal 发出通知
        """
        begin_time = (datetime.now() - timedelta(days=self.days)).strftime("%Y-%m-%d")
        end_time = datetime.now().strftime("%Y-%m-%d")
        if self.stock_list is None:
            self.log_signal.emit('正在获取股票列表...')
            self.stock_list = get_tradable_stocks()
            if self.isInterruptionRequested():
                return
            if self.stock_list.empty:
                self.error.emit('获取股票列表失败或没有符合条件的股票')
                return
        total = len(self.stock_list)
        success_count = 0
        fail_count = 0

        for idx, row in self.stock_list.iterrows():
            if self.isInterruptionRequested():
                break

            code = row['代码']
            name = row['名称']
            self.progress.emit(idx + 1, total, f"{code} {name}")
            self.log_signal.emit(f"🔍 扫描 {code} {name}...")

            try:
                chan = CChan(
                    code=code,
                    begin_time=begin_time,
                    end_time=end_time,
                    data_src=DATA_SRC.AKSHARE,
                    lv_list=[KL_TYPE.K_DAY],
                    config=self.config,
                    autype=AUTYPE.QFQ,
                )

                if self.isInterruptionRequested():
                    break

                # 检查最近15天是否有数据
                if len(chan[0]) == 0:
                    fail_count += 1
                    self.log_signal.emit(f"⏭️ {code} {name}: 无K线数据")
                    continue
                last_klu = chan[0][-1][-1]
                last_time = last_klu.time
                last_date = datetime(last_time.year, last_time.month, last_time.day)
                if (datetime.now() - last_date).days > 15:
                    fail_count += 1
                    self.log_signal.emit(f"⏸️ {code} {name}: 停牌超过15天")
                    continue

                # 检查是否有买点（只找最近3天内出现的买点）
                bsp_list = chan.get_latest_bsp(number=0)
                cutoff_date = (datetime.now() - timedelta(days=3)).date()
                buy_points = [
                    bsp for bsp in bsp_list
                    if bsp.is_buy and datetime(bsp.klu.time.year, bsp.klu.time.month, bsp.klu.time.day).date() >= cutoff_date
                ]

                if buy_points:
                    # 获取最近的买点
                    latest_buy = buy_points[0]
                    self.log_signal.emit(f"✅ {code} {name}: 发现买点 {latest_buy.type2str()}")
                    self.found_signal.emit({
                        'code': code,
                        'name': name,
                        'price': row['最新价'],
                        'change': row['涨跌幅'],
                        'bsp_type': latest_buy.type2str(),
                        'bsp_time': str(latest_buy.klu.time),
                        'chan': chan,
                    })
                else:
                    self.log_signal.emit(f"➖ {code} {name}: 无近期买点")
                success_count += 1
            except Exception as e:
                if self.isInterruptionRequested():
                    break
                fail_count += 1
                self.log_signal.emit(f"❌ {code} {name}: {str(e)[:50]}")
                continue

        self.success_count = success_count
        self.fail_count = fail_count


class SingleAnalysisThread(QThread):
    """
    单只股票分析的后台线程

    用于分析用户手动输入的股票代码，避免阻塞 UI。

    Signals:
        result: (CChan) 分析完成，返回 CChan 对象
        error: (str) 分析出错时返回错误信息
    """
    result = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, code, config, days=365):
        """
        初始化分析线程

        Args:
            code: str, 股票代码（如 '000001'）
            config: CChanConfig, 缠论配置
            days: int, 获取多少天的历史数据
        """
        super().__init__()
        self.code = code
        self.config = config
        self.days = days

    def run(self):
        """执行缠论分析，完成后通过信号返回结果"""
        try:
            begin_time = (datetime.now() - timedelta(days=self.days)).strftime("%Y-%m-%d")
            end_time = datetime.now().strftime("%Y-%m-%d")

            chan = CChan(
                code=self.code,
                begin_time=begin_time,
                end_time=end_time,
                data_src=DATA_SRC.AKSHARE,
                lv_list=[KL_TYPE.K_DAY],
                config=self.config,
                autype=AUTYPE.QFQ,
            )
            if not self.isInterruptionRequested():
                self.result.emit(chan)
        except Exception as e:
            if not self.isInterruptionRequested():
                self.error.emit(str(e))


class ChanPlotCanvas(FigureCanvas):
    """
    嵌入 PyQt 的 Matplotlib 画布

    用于在 GUI 中显示缠论分析图表，包括K线、笔、线段、中枢等。

    Args:
        parent: 父控件
        width: 图表宽度（英寸）
        height: 图表高度（英寸）
    """

    def __init__(self, parent=None, width=12, height=8):
        self.fig = Figure(figsize=(width, height), dpi=100, facecolor='#ffffff')
        super().__init__(self.fig)
        self.setParent(parent)
        self.setMinimumHeight(400)

    def clear(self):
        """清空画布内容"""
        self.fig.clear()
        self.draw()


class AkshareGUI(QMainWindow):
    """
    A股缠论买点扫描器主窗口

    主要功能:
        - 批量扫描: 自动获取所有可交易股票，逐一分析寻找买点
        - 单股分析: 手动输入股票代码进行缠论分析
        - 图表显示: 可视化展示K线、笔、线段、中枢、买卖点、MACD

    界面布局:
        - 左侧面板: 扫描控制、单股输入、买点列表、扫描日志
        - 右侧面板: 图表显示区域，支持缩放和导航
    """

    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        self.chan = None  # 当前分析的 CChan 对象
        self.scan_thread = None  # 批量扫描线程
        self.analysis_thread = None  # 单股分析线程
        self._closing = False
        self._analysis_request = 0
        self._pending_analysis = None
        self._scan_error = None
        self.stock_cache = {}  # 缓存已分析的股票 {code: CChan}
        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle('A股缠论买点扫描器 - Powered by chan.py')
        self.setGeometry(100, 100, 1600, 900)

        # 创建中央 widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 8)

        # 左侧控制面板和股票列表
        left_panel = self.create_left_panel()

        # 右侧图表区域
        right_panel = self.create_chart_panel()

        # 使用分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setChildrenCollapsible(False)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([450, 1150])

        main_layout.addWidget(splitter)

        # 状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage('就绪 - 点击"开始扫描"分析所有股票')

    def create_left_panel(self):
        """创建左侧面板"""
        panel = QWidget()
        panel.setMinimumWidth(420)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(12)

        # 扫描控制
        scan_group = QGroupBox("扫描设置")
        scan_layout = QVBoxLayout(scan_group)

        # 笔严格模式
        self.bi_strict_cb = QCheckBox("笔严格模式")
        self.bi_strict_cb.setChecked(True)
        scan_layout.addWidget(self.bi_strict_cb)

        # 扫描按钮
        btn_layout = QHBoxLayout()
        self.scan_btn = QPushButton("开始扫描")
        self.scan_btn.clicked.connect(self.start_scan)
        self.scan_btn.setObjectName("scanButton")
        btn_layout.addWidget(self.scan_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop_scan)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setObjectName("stopButton")
        btn_layout.addWidget(self.stop_btn)
        scan_layout.addLayout(btn_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        scan_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        scan_layout.addWidget(self.progress_label)

        layout.addWidget(scan_group)

        # 单只股票分析
        single_group = QGroupBox("单只股票分析")
        single_layout = QVBoxLayout(single_group)

        code_row = QHBoxLayout()
        code_row.addWidget(QLabel("股票代码:"))
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("如: 000001")
        code_row.addWidget(self.code_input)

        self.analyze_btn = QPushButton("分析")
        self.analyze_btn.clicked.connect(self.analyze_single)
        code_row.addWidget(self.analyze_btn)
        single_layout.addLayout(code_row)

        layout.addWidget(single_group)

        # 买点股票列表
        list_group = QGroupBox("买点股票列表")
        list_layout = QVBoxLayout(list_group)

        self.stock_table = QTableWidget()
        self.stock_table.setColumnCount(5)
        self.stock_table.setHorizontalHeaderLabels(['代码', '名称', '现价', '涨跌%', '买点'])
        self.stock_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stock_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.stock_table.setAlternatingRowColors(True)
        self.stock_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.stock_table.verticalHeader().setVisible(False)
        self.stock_table.verticalHeader().setDefaultSectionSize(34)
        self.stock_table.setWordWrap(False)
        self.stock_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.stock_table.cellClicked.connect(self.on_stock_clicked)
        list_layout.addWidget(self.stock_table)

        # 列表操作
        list_btn_layout = QHBoxLayout()
        self.copy_codes_btn = QPushButton("复制全部代码")
        self.copy_codes_btn.setToolTip("复制列表中的全部股票代码，每行一个，保留前导零")
        self.copy_codes_btn.setEnabled(False)
        self.copy_codes_btn.clicked.connect(self.copy_stock_codes)
        list_btn_layout.addWidget(self.copy_codes_btn)

        self.clear_list_btn = QPushButton("清空列表")
        self.clear_list_btn.clicked.connect(self.clear_stock_list)
        list_btn_layout.addWidget(self.clear_list_btn)
        list_layout.addLayout(list_btn_layout)

        layout.addWidget(list_group, 1)

        # 日志区域
        log_group = QGroupBox("扫描日志")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.document().setMaximumBlockCount(2000)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)

        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.clicked.connect(lambda: self.log_text.clear())
        log_layout.addWidget(clear_log_btn)

        layout.addWidget(log_group)

        return panel

    def create_chart_panel(self):
        """创建右侧图表面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 0, 0, 0)

        # 绘图配置
        config_layout = QHBoxLayout()

        self.plot_kline_cb = QCheckBox("K线")
        self.plot_kline_cb.setChecked(True)
        config_layout.addWidget(self.plot_kline_cb)

        self.plot_bi_cb = QCheckBox("笔")
        self.plot_bi_cb.setChecked(True)
        config_layout.addWidget(self.plot_bi_cb)

        self.plot_seg_cb = QCheckBox("线段")
        self.plot_seg_cb.setChecked(True)
        config_layout.addWidget(self.plot_seg_cb)

        self.plot_zs_cb = QCheckBox("中枢")
        self.plot_zs_cb.setChecked(True)
        config_layout.addWidget(self.plot_zs_cb)

        self.plot_bsp_cb = QCheckBox("买卖点")
        self.plot_bsp_cb.setChecked(True)
        config_layout.addWidget(self.plot_bsp_cb)

        self.plot_macd_cb = QCheckBox("MACD")
        self.plot_macd_cb.setChecked(True)
        config_layout.addWidget(self.plot_macd_cb)

        config_layout.addStretch()

        # 刷新按钮
        self.refresh_btn = QPushButton("刷新图表")
        self.refresh_btn.clicked.connect(self.refresh_chart)
        config_layout.addWidget(self.refresh_btn)

        layout.addLayout(config_layout)

        # matplotlib 画布
        self.canvas = ChanPlotCanvas(panel, width=12, height=8)
        self.toolbar = NavigationToolbar(self.canvas, panel)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        return panel

    def get_chan_config(self):
        """
        获取缠论分析配置

        Returns:
            CChanConfig: 包含笔严格模式、买卖点类型等配置的对象
        """
        return CChanConfig({
            "bi_strict": self.bi_strict_cb.isChecked(),  # 笔严格模式
            "trigger_step": False,  # 不启用逐步触发模式
            "skip_step": 0,
            "divergence_rate": float("inf"),  # 背驰比率
            "bsp2_follow_1": False,  # 二类买卖点不跟随一类
            "bsp3_follow_1": False,  # 三类买卖点不跟随一类
            "min_zs_cnt": 0,  # 最小中枢数量
            "bs1_peak": False,
            "macd_algo": "peak",  # MACD 算法
            "bs_type": "1,1p,2,2s,3a,3b",  # 启用的买卖点类型
            "print_warning": False,
            "zs_algo": "normal",  # 中枢算法
        })

    def get_plot_config(self):
        """
        获取图表绑定配置

        Returns:
            dict: 包含各图层显示开关的配置字典
        """
        return {
            "plot_kline": self.plot_kline_cb.isChecked(),  # 显示K线
            "plot_kline_combine": True,  # 显示合并K线
            "plot_bi": self.plot_bi_cb.isChecked(),  # 显示笔
            "plot_seg": self.plot_seg_cb.isChecked(),  # 显示线段
            "plot_zs": self.plot_zs_cb.isChecked(),  # 显示中枢
            "plot_macd": self.plot_macd_cb.isChecked(),  # 显示MACD
            "plot_bsp": self.plot_bsp_cb.isChecked(),  # 显示买卖点
        }

    def start_scan(self):
        """开始批量扫描所有可交易股票"""
        if self._closing or self.scan_thread is not None:
            return
        self.clear_stock_list()
        self._scan_error = None
        self.scan_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.clear_list_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.progress_label.setText('正在获取股票列表...')
        self.statusBar.showMessage('正在获取股票列表...')

        self.scan_thread = ScanThread(None, self.get_chan_config(), days=365)
        self.scan_thread.progress.connect(self.on_scan_progress)
        self.scan_thread.found_signal.connect(self.on_buy_point_found)
        self.scan_thread.error.connect(self.on_scan_error)
        self.scan_thread.finished.connect(self.on_scan_finished)
        self.scan_thread.log_signal.connect(self.on_log_message)
        self.scan_thread.start()

    def stop_scan(self):
        """协作取消，等待当前数据请求返回后安全退出。"""
        if self.scan_thread:
            self.scan_thread.stop()
            self.stop_btn.setEnabled(False)
            self.progress_label.setText('正在停止，等待当前数据请求结束...')
            self.statusBar.showMessage('正在停止扫描，等待当前数据请求结束...')

    def on_scan_error(self, message):
        self._scan_error = message
        self.on_log_message(message)

    def on_scan_progress(self, current, total, stock_info):
        """扫描进度更新"""
        if self._closing or (self.scan_thread and self.scan_thread.cancelled):
            return
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"进度: {current}/{total} - {stock_info}")

    def on_log_message(self, msg):
        """显示日志消息"""
        self.log_text.append(msg)

    def on_buy_point_found(self, data):
        """
        发现买点的回调函数

        Args:
            data: dict, 包含股票代码、名称、价格、买点类型、CChan对象等信息
        """
        if self._closing or (self.scan_thread and self.scan_thread.cancelled):
            return
        row = self.stock_table.rowCount()
        self.stock_table.insertRow(row)
        self.stock_table.setItem(row, 0, QTableWidgetItem(data['code']))
        self.stock_table.setItem(row, 1, QTableWidgetItem(data['name']))
        self.stock_table.setItem(row, 2, QTableWidgetItem(f"{data['price']:.2f}"))
        self.stock_table.setItem(row, 3, QTableWidgetItem(f"{data['change']:.2f}%"))
        self.stock_table.setItem(row, 4, QTableWidgetItem(f"{data['bsp_type']} ({data['bsp_time']})"))

        # 缓存 chan 对象
        self.stock_cache[data['code']] = data['chan']
        self.copy_codes_btn.setEnabled(True)

    def on_scan_finished(self):
        """使用 QThread 原生 finished，确保线程退出后才能重新开始。"""
        thread = self.scan_thread
        self.scan_thread = None
        stopped = thread.cancelled
        success_count, fail_count = thread.success_count, thread.fail_count
        thread.deleteLater()
        if self._closing:
            return
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.clear_list_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        state = '已停止' if stopped else ('扫描失败' if self._scan_error else '扫描完成')
        summary = (f'{state}: 成功{success_count}只, 跳过/失败{fail_count}只, '
                   f'发现{self.stock_table.rowCount()}只买点股票')
        self.statusBar.showMessage(self._scan_error or summary)
        self.progress_label.setText(summary)

    def on_stock_clicked(self, row, col):
        """点击股票列表"""
        code = self.stock_table.item(row, 0).text()
        name = self.stock_table.item(row, 1).text()

        if code in self.stock_cache:
            self._analysis_request += 1
            self._pending_analysis = None
            self.chan = self.stock_cache[code]
            self.plot_chart()
            self.statusBar.showMessage(f'显示: {code} {name}')
        else:
            # 重新分析
            self.analyze_stock(code)

    def analyze_single(self):
        """分析单只股票"""
        code = self.code_input.text().strip()
        if not code:
            QMessageBox.warning(self, "警告", "请输入股票代码")
            return
        self.analyze_stock(code)

    def analyze_stock(self, code):
        """分析指定股票"""
        if self._closing:
            return
        self._analysis_request += 1
        self._pending_analysis = (self._analysis_request, code, self.get_chan_config())
        self.statusBar.showMessage(f'正在分析 {code}...')
        if self.analysis_thread is None:
            self.start_pending_analysis()

    def start_pending_analysis(self):
        if self._closing or self._pending_analysis is None:
            return
        request, code, config = self._pending_analysis
        self._pending_analysis = None
        thread = SingleAnalysisThread(code, config, days=365)
        thread.request_id = request
        self.analysis_thread = thread
        thread.result.connect(self.on_analysis_finished)
        thread.error.connect(self.on_analysis_error)
        thread.finished.connect(self.on_analysis_thread_finished)
        thread.start()

    def on_analysis_thread_finished(self):
        thread = self.analysis_thread
        self.analysis_thread = None
        thread.deleteLater()
        self.start_pending_analysis()

    def on_analysis_finished(self, chan):
        if self._closing or self.sender().request_id != self._analysis_request:
            return
        self.chan = chan
        self.plot_chart()
        self.statusBar.showMessage(f'分析完成: {chan.code}')

    def on_analysis_error(self, error_msg):
        if self._closing or self.sender().request_id != self._analysis_request:
            return
        QMessageBox.critical(self, "分析错误", error_msg)
        self.statusBar.showMessage('分析失败')

    def closeEvent(self, event):
        """不销毁运行中的 QThread；保持事件循环直到后台请求结束。"""
        self._closing = True
        self._pending_analysis = None
        for thread in (self.scan_thread, self.analysis_thread):
            if thread is not None:
                thread.requestInterruption()
        if any(thread is not None and thread.isRunning()
               for thread in (self.scan_thread, self.analysis_thread)):
            event.ignore()
            self.setEnabled(False)
            self.statusBar.showMessage('正在退出，等待后台数据请求结束...')
            QTimer.singleShot(100, self.close)
        else:
            event.accept()

    def plot_chart(self):
        """
        绑定当前股票的缠论分析图表

        使用 CPlotDriver 生成图表，显示K线、笔、线段、中枢等元素。
        图表大小会根据画布宽度自动调整。
        """
        if not self.chan:
            return

        try:
            from Plot.PlotDriver import CPlotDriver

            # 关闭旧的 figure 释放内存
            plt.close(self.canvas.figure)

            plot_config = self.get_plot_config()

            # 获取控件宽度，计算合适的图表尺寸
            canvas_width = self.canvas.width()
            dpi = 100
            fig_width = canvas_width / dpi
            fig_height = fig_width * 0.5  # 宽高比 2:1

            plot_para = {
                "figure": {
                    "x_range": 200,
                    "w": fig_width,
                    "h": fig_height,
                }
            }

            plot_driver = CPlotDriver(self.chan, plot_config=plot_config, plot_para=plot_para)
            style_chart(plot_driver.figure)

            self.canvas.fig = plot_driver.figure
            self.canvas.figure = plot_driver.figure
            plot_driver.figure.set_canvas(self.canvas)
            self.canvas.draw()
            self.toolbar.update()
        except Exception as e:
            QMessageBox.critical(self, "绑定错误", str(e))

    def refresh_chart(self):
        """刷新图表"""
        self.plot_chart()

    def copy_stock_codes(self):
        """按列表顺序复制全部股票代码，每行一个，保留前导零。"""
        codes = []
        for row in range(self.stock_table.rowCount()):
            item = self.stock_table.item(row, 0)
            if item is not None and item.text().strip():
                codes.append(item.text().strip())
        if not codes:
            self.statusBar.showMessage('列表为空，没有可复制的股票代码')
            return
        QApplication.clipboard().setText('\n'.join(codes))
        self.statusBar.showMessage(f'已复制 {len(codes)} 个股票代码到剪贴板')

    def clear_stock_list(self):
        """清空股票列表"""
        self.stock_table.setRowCount(0)
        self.stock_cache.clear()
        self.copy_codes_btn.setEnabled(False)
        self.statusBar.showMessage('列表已清空')


def main():
    """程序入口函数，创建并运行 GUI 应用"""
    app = QApplication(sys.argv)
    apply_theme(app)

    window = AkshareGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
