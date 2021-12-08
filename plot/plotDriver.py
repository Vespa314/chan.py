from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt
from .plot_meta import CChanPlotMeta
from common.CEnum import KLINE_DIR, FX_TYPE
from chan import CChan


def parse_plot_para(paras, _type):
    res = {}
    type_key = _type+"_"
    for para, v in paras.items():
        if para.startswith(type_key):
            res[para.replace(type_key, "")] = v
    return res


def parse_plot_config(plot_config):
    if isinstance(plot_config, dict):
        return plot_config
    elif isinstance(plot_config, str):
        return dict([(k.strip().lower(), True) for k in plot_config.split(",")])
    elif isinstance(plot_config, list):
        return dict([(k.strip().lower(), True) for k in plot_config])
    else:
        raise Exception("plot_config only support list/str/dict")


def create_height_ratios_para(n, r):
    res = []
    for _ in range(n):
        res.append(1)
        res.append(r)
    return res


def set_x_tick(ax, x_limits, tick):
    ax.set_xlim(x_limits[0], x_limits[1]+1)
    ax.set_xticks(range(x_limits[0], x_limits[1], max([1, int((x_limits[1]-x_limits[0])/10)])))
    ax.set_xticklabels([tick[i] for i in ax.get_xticks()], rotation=20)


def cal_y_range(meta: CChanPlotMeta, ax):
    x_begin = ax.get_xlim()[0]
    y_min = float("inf")
    y_max = float("-inf")
    for klc_meta in meta.klc_list:
        if klc_meta.klu_list[-1].idx < x_begin:
            continue  # 不绘制范围外的
        if klc_meta.high > y_max:
            y_max = klc_meta.high
        if klc_meta.low < y_min:
            y_min = klc_meta.low
    return (y_min, y_max)


def create_figure(plot_macd, figure_config, lv_cnt):
    if plot_macd:
        macd_h_ration = figure_config.get('macd_h', 0.3)
        figure_size = (figure_config.get('w', 20), figure_config.get('h', 10)*lv_cnt*(1+macd_h_ration))
        figure, axes = plt.subplots(
                                lv_cnt*2,
                                1,
                                figsize=figure_size,
                                gridspec_kw={'height_ratios': create_height_ratios_para(lv_cnt, macd_h_ration)}
                            )
        axes = zip(axes[::2], axes[1::2])
    else:
        figure_size = (figure_config.get('w', 20), figure_config.get('h', 10)*lv_cnt)
        figure, axes = plt.subplots(lv_cnt, 1, figsize=figure_size)
        if lv_cnt == 1:
            axes = [axes]
    return figure, axes


def cal_x_limit(meta, x_range):
    X_LEN = meta.klu_len
    x_range = x_range
    x_limits = [X_LEN-x_range, X_LEN-1] if x_range and X_LEN > x_range else [0, X_LEN-1]
    return x_limits


def set_grid(ax, config):
    if config is None:
        return
    if config is True or config == "xy":
        ax.grid(True)
        return
    if config in ("x", "y"):
        ax.grid(True, axis=config)
        return
    raise Exception(f"unsupport grid config={config}")


class CPlot_driver:
    def __init__(self, chan: CChan, plot_config='', plot_para={}):
        plot_config = parse_plot_config(plot_config)
        figure_config = parse_plot_para(plot_para, "figure")

        plot_metas = [CChanPlotMeta(kl_data) for kl_data in chan.kl_datas.values()]
        if figure_config.get("only_top_lv", False):
            plot_metas = [plot_metas[0]]
        self.lv_lst = [lv for lv in chan.kl_datas.keys()][:len(plot_metas)]

        x_range = figure_config.get("x_range", 0)
        plot_macd = plot_config.get("plot_macd", False)
        self.figure, axes = create_figure(plot_macd, figure_config, len(plot_metas))

        sseg_begin = 0
        slv_seg_cnt = parse_plot_para(plot_para, "seg").get("sub_lv_cnt", None)
        sbi_begin = 0
        slv_bi_cnt = parse_plot_para(plot_para, "bi").get("sub_lv_cnt", None)
        srange_begin = 0
        assert slv_seg_cnt is None or slv_bi_cnt is None, "you can set at most one of seg_sub_lv_cnt/bi_sub_lv_cnt"

        for _ax, meta, lv in zip(axes, plot_metas, self.lv_lst):
            ax, ax_macd = _ax if plot_macd else (_ax, None)
            set_grid(ax, figure_config.get("grid", True))
            ax.set_title(f"{lv}", fontsize=16, loc='left', color='r')

            x_limits = cal_x_limit(meta, x_range)
            if lv != self.lv_lst[0]:
                if sseg_begin != 0 or sbi_begin != 0:
                    x_limits[0] = max(sseg_begin, sbi_begin)
                elif srange_begin != 0:
                    x_limits[0] = srange_begin
            set_x_tick(ax, x_limits, meta.datetick)
            if ax_macd:
                set_x_tick(ax_macd, x_limits, meta.datetick)
            self.y_min, self.y_max = cal_y_range(meta, ax)  # 需要先设置 x_tick后计算

            if plot_config.get("plot_kline", False):
                self.draw_klu(meta, ax, **parse_plot_para(plot_para, "ukl"))
            if plot_config.get("plot_kline_combine", False):
                self.draw_klc(meta, ax, **parse_plot_para(plot_para, "ckl"))
            if plot_config.get("plot_bi", False):
                self.draw_bi(meta, ax, lv, **parse_plot_para(plot_para, "bi"))
            if plot_config.get("plot_seg", False):
                self.draw_seg(meta, ax, lv, **parse_plot_para(plot_para, "seg"))
            if plot_config.get("plot_eigen", False):
                self.draw_eigen(meta, ax, **parse_plot_para(plot_para, "eigen"))
            if plot_config.get("plot_zs", False):
                self.draw_zs(meta, ax, **parse_plot_para(plot_para, "zs"))
            if plot_config.get("plot_macd", False):
                self.draw_macd(meta, ax_macd, x_limits, **parse_plot_para(plot_para, "macd"))
            if plot_config.get("plot_mean", False):
                self.draw_mean(meta, ax, **parse_plot_para(plot_para, "mean"))
            if plot_config.get("plot_bsp", False):
                self.draw_bs_point(meta, ax, **parse_plot_para(plot_para, "bsp"))
            if plot_config.get("plot_cbsp", False):
                self.draw_cbs_point(meta, ax, **parse_plot_para(plot_para, "cbsp"))
            if plot_config.get("plot_extrainfo", False):
                self.draw_extrainfo(meta, ax.twinx(), **parse_plot_para(plot_para, "extrainfo"))

            if lv != self.lv_lst[-1]:
                sseg_begin = meta.sub_last_kseg_start_idx(slv_seg_cnt)
                sbi_begin = meta.sub_last_kbi_start_idx(slv_bi_cnt)
                if x_range != 0:
                    srange_begin = meta.sub_range_start_idx(x_range)

            ax.set_ylim(self.y_min, self.y_max)

    def save2img(self, path):
        plt.savefig(path, bbox_inches='tight')

    def draw_klu(self, meta: CChanPlotMeta, ax, width=0.4, rugd=True):
        # rugd: red up green down
        up_color = 'r' if rugd else 'g'
        down_color = 'g' if rugd else 'r'

        x_begin = ax.get_xlim()[0]
        for kl in meta.klu_iter():
            i = kl.idx
            if i+width < x_begin:
                continue  # 不绘制范围外的
            if kl.close > kl.open:
                ax.add_patch(
                    Rectangle((i - width / 2, kl.open), width, kl.close - kl.open, fill=False, color=up_color))
                ax.plot([i, i], [kl.low, kl.open], up_color)
                ax.plot([i, i], [kl.close, kl.high], up_color)
            else:  # 画阴线
                ax.add_patch(Rectangle((i - width / 2, kl.open), width, kl.close - kl.open, color=down_color))
                ax.plot([i, i], [kl.low, kl.high], color=down_color)

    def draw_klc(self, meta: CChanPlotMeta, ax, width=0.4):
        color_type = {FX_TYPE.TOP: 'red', FX_TYPE.BOTTOM: 'blue', KLINE_DIR.UP: 'green', KLINE_DIR.DOWN: 'green'}
        x_begin = ax.get_xlim()[0]

        for klc_meta in meta.klc_list:
            if klc_meta.klu_list[-1].idx+width < x_begin:
                continue  # 不绘制范围外的
            ax.add_patch(
                Rectangle(
                    (klc_meta.begin_idx - width, klc_meta.low),
                    klc_meta.end_idx - klc_meta.begin_idx + width*2,
                    klc_meta.high - klc_meta.low,
                    fill=False,
                    color=color_type[klc_meta.type]))

    def draw_bi(self, meta: CChanPlotMeta, ax, lv, emph_type=[], color='black', emph_color="red", show_num=False, num_color="red", sub_lv_cnt=None, facecolor='green', alpha=0.1):
        x_begin = ax.get_xlim()[0]
        for bi in meta.bi_list:
            if bi.end_x < x_begin:
                continue
            clr = emph_color if bi.type in emph_type else color
            if bi.id_sure:
                ax.plot([bi.begin_x, bi.end_x], [bi.begin_y, bi.end_y], color=clr)
            else:
                ax.plot([bi.begin_x, bi.end_x], [bi.begin_y, bi.end_y], linestyle='dashed', color=clr)
            if show_num:
                ax.text((bi.begin_x+bi.end_x)/2, (bi.begin_y+bi.end_y)/2, f'{bi.idx}', fontsize=15, color=num_color)
        if sub_lv_cnt is not None and len(self.lv_lst) > 1 and lv != self.lv_lst[-1]:
            if sub_lv_cnt >= len(meta.bi_list):
                return
            else:
                begin_idx = meta.bi_list[-sub_lv_cnt].begin_x
            y_begin, y_end = ax.get_ylim()
            x_end = int(ax.get_xlim()[1])
            ax.fill_between(range(begin_idx, int(x_end)+1), y_begin, y_end, facecolor=facecolor, alpha=alpha)

    def draw_seg(self, meta: CChanPlotMeta, ax, lv, width=5, color="r", sub_lv_cnt=None, facecolor='green', alpha=0.1):
        x_begin = ax.get_xlim()[0]

        for seg_meta in meta.seg_list:
            if seg_meta.end_x < x_begin:
                continue
            if seg_meta.is_sure:
                ax.plot([seg_meta.begin_x, seg_meta.end_x], [seg_meta.begin_y, seg_meta.end_y], color=color, linewidth=width)
            else:
                ax.plot([seg_meta.begin_x, seg_meta.end_x], [seg_meta.begin_y, seg_meta.end_y], color=color, linewidth=width, linestyle='dashed')
        if sub_lv_cnt is not None and len(self.lv_lst) > 1 and lv != self.lv_lst[-1]:
            if sub_lv_cnt >= len(meta.seg_list):
                return
            else:
                begin_idx = meta.seg_list[-sub_lv_cnt].begin_x
            y_begin, y_end = ax.get_ylim()
            x_end = int(ax.get_xlim()[1])
            ax.fill_between(range(begin_idx, x_end+1), y_begin, y_end, facecolor=facecolor, alpha=alpha)

    def draw_eigen(self, meta: CChanPlotMeta, ax, color_top="r", color_bottom="b", color_up='green', color_down='pink', aplha=0.5, only_peak=True):
        x_begin = ax.get_xlim()[0]

        for eigen_meta in meta.bi_eigen_lst:
            if eigen_meta.begin_x+eigen_meta.w < x_begin:
                continue
            if eigen_meta.fx == FX_TYPE.TOP:
                color = color_top
            elif eigen_meta.fx == FX_TYPE.BOTTOM:
                color = color_bottom
            elif only_peak:
                continue
            elif eigen_meta.is_up:
                color = color_up
            else:
                color = color_down
            ax.add_patch(Rectangle((eigen_meta.begin_x, eigen_meta.begin_y),
                         eigen_meta.w,
                         eigen_meta.h,
                         fill=True,
                         alpha=aplha,
                         color=color))

    def draw_zs(self, meta: CChanPlotMeta, ax, color='k', linewidth=2, sub_linewidth=0.5):
        if linewidth < 2:
            linewidth = 2
        x_begin = ax.get_xlim()[0]
        for zs_meta in meta.zs_lst:
            if zs_meta.begin+zs_meta.w < x_begin:
                continue
            line_style = '-' if zs_meta.is_sure else '--'
            ax.add_patch(Rectangle((zs_meta.begin, zs_meta.low), zs_meta.w, zs_meta.h, fill=False, color=color, linewidth=linewidth, linestyle=line_style))
            for sub_zs_meta in zs_meta.sub_zs_lst:
                ax.add_patch(Rectangle((sub_zs_meta.begin, sub_zs_meta.low), sub_zs_meta.w, sub_zs_meta.h, fill=False, color=color, linewidth=sub_linewidth, linestyle=line_style))

    def draw_macd(self, meta: CChanPlotMeta, ax, x_limits, width=0.4):
        macd_lst = [klu.macd for klu in meta.klu_iter()]
        assert macd_lst[0] is not None, "you can't draw macd until you delete macd_metric=False"

        x_begin = x_limits[0]
        x_idx = range(len(macd_lst))
        dif_line = [macd.DIF for macd in macd_lst]
        dea_line = [macd.DEA for macd in macd_lst]
        macd_bar = [macd.macd for macd in macd_lst]
        y_min = min([min(dif_line[x_begin:]), min(dea_line[x_begin:]), min(macd_bar[x_begin:])])
        y_max = max([max(dif_line[x_begin:]), max(dea_line[x_begin:]), max(macd_bar[x_begin:])])
        ax.plot(x_idx, dif_line, "#FFA500")
        ax.plot(x_idx, dea_line, "#0000ff")
        _bar = ax.bar(x_idx, macd_bar, color="r", width=width)
        for idx, macd in enumerate(macd_bar):
            if macd < 0:
                _bar[idx].set_color("#006400")
        ax.set_ylim(y_min, y_max)

    def draw_mean(self, meta: CChanPlotMeta, ax):
        mean_lst = [klu.means for klu in meta.klu_iter()]
        Ts = list(mean_lst[0].keys())
        cmap = plt.cm.get_cmap('hsv', max([10, len(Ts)]))
        cmap_idx = 0
        for T in Ts:
            mean_arr = [mean_dict[T] for mean_dict in mean_lst]
            ax.plot(range(len(mean_arr)), mean_arr, c=cmap(cmap_idx), label=f'{T} meanline')
            cmap_idx += 1
        ax.legend()

    def draw_bs_point(self, meta: CChanPlotMeta, ax, buy_color='r', sell_color='g', fontsize=15, arrow_l=0.15, arrow_h=0.2, arrow_w=1):
        x_begin = ax.get_xlim()[0]
        y_range = self.y_max-self.y_min
        for bsp in meta.bs_point_lst:
            if bsp.x < x_begin:
                continue
            color = buy_color if bsp.is_buy else sell_color
            verticalalignment = 'top' if bsp.is_buy else 'bottom'

            arrow_dir = 1 if bsp.is_buy else -1
            arrow_len = arrow_l*y_range
            arrow_head = arrow_len*arrow_h
            ax.text(bsp.x,
                    bsp.y-arrow_len*arrow_dir,
                    f'{bsp.desc()}',
                    fontsize=fontsize,
                    color=color,
                    verticalalignment=verticalalignment,
                    horizontalalignment='center')
            ax.arrow(bsp.x,
                     bsp.y-arrow_len*arrow_dir,
                     0,
                     (arrow_len-arrow_head)*arrow_dir,
                     head_width=arrow_w,
                     head_length=arrow_head,
                     color=color)
            if bsp.y-arrow_len*arrow_dir < self.y_min:
                self.y_min = bsp.y-arrow_len*arrow_dir
            if bsp.y-arrow_len*arrow_dir > self.y_max:
                self.y_max = bsp.y-arrow_len*arrow_dir

    def draw_cbs_point(self, meta: CChanPlotMeta, ax, buy_color='r', sell_color='g', fontsize=15, arrow_l=0.3, arrow_h=0.1, arrow_w=1, plot_cover=True):
        x_begin = ax.get_xlim()[0]
        y_range = self.y_max-self.y_min
        for cbsp in meta.custom_bsp_lst:
            if cbsp.x < x_begin:
                continue
            color = buy_color if cbsp.is_buy else sell_color
            verticalalignment = 'top' if cbsp.is_buy else 'bottom'
            arrow_dir = 1 if cbsp.is_buy else -1
            arrow_len = arrow_l*y_range
            arrow_head = arrow_len*arrow_h
            ax.text(cbsp.x,
                    cbsp.y-arrow_len*arrow_dir,
                    f'{cbsp.desc()}',
                    fontsize=fontsize,
                    color=color,
                    verticalalignment=verticalalignment,
                    horizontalalignment='center',
                    rotation=45)
            ax.arrow(cbsp.x,
                     cbsp.y-arrow_len*arrow_dir,
                     0,
                     (arrow_len-arrow_head)*arrow_dir,
                     head_width=arrow_w,
                     head_length=arrow_head,
                     color=color,
                     linestyle=(0, (3, 10, 5, 10))
                     )
            if cbsp.y-arrow_len*arrow_dir < self.y_min:
                self.y_min = cbsp.y-arrow_len*arrow_dir
            if cbsp.y-arrow_len*arrow_dir > self.y_max:
                self.y_max = cbsp.y-arrow_len*arrow_dir
            if plot_cover:
                ax.plot([cbsp.x-0.5, cbsp.x+0.5], [cbsp.sl_thred, cbsp.sl_thred], c=color)

            for closeAction in cbsp.close_action:
                ax.arrow(cbsp.x,
                         cbsp.y-arrow_len*arrow_dir,
                         closeAction.x-cbsp.x,
                         arrow_len*arrow_dir + (closeAction.y-cbsp.y),
                         color=color,
                         )

    def draw_extrainfo(self,
                       meta: CChanPlotMeta,
                       ax,
                       info="volume",
                       plot_curve=True,
                       plot_outliner=True,
                       color='b',
                       outline_color="orange",
                       thred=5.0,
                       plot_mean=False,
                       ):
        if plot_curve:
            if info == "volumn":
                data = [klu.trade_info.volume for klu in meta.klu_iter()]
            elif info == "turnover":
                data = [klu.trade_info.turnover for klu in meta.klu_iter()]
            elif info == "turnover_rate":
                data = [klu.trade_info.turnover_rate for klu in meta.klu_iter()]
            else:
                raise Exception(f"unsupport info type = {info}, you can use volumn/turnover/turnover_rate")
            ax.plot(range(len(data)), data, c=color)
            ax.set_ylabel(info)
        if plot_outliner:
            y0, y1 = ax.get_ylim()
            if info == "volumn":
                idx_lst = [idx for idx, klu in enumerate(meta.klu_iter()) if klu.trade_info.volume_od_score > thred]
                mean_line = [klu.trade_info.volume_mean for klu in meta.klu_iter()]
            elif info == "turnover":
                idx_lst = [idx for idx, klu in enumerate(meta.klu_iter()) if klu.trade_info.turnover_od_score > thred]
                mean_line = [klu.trade_info.turnover_mean for klu in meta.klu_iter()]
            elif info == "turnover_rate":
                idx_lst = [idx for idx, klu in enumerate(meta.klu_iter()) if klu.trade_info.turnover_rate_od_score > thred]
                mean_line = [klu.trade_info.turnover_rate_mean for klu in meta.klu_iter()]
            else:
                raise Exception(f"unsupport info type = {info}, you can use volumn/turnover/turnover_rate")
            if plot_mean:
                ax.plot(mean_line)
            for idx in idx_lst:
                ax.plot([idx, idx], [y0, y1], c=outline_color)
