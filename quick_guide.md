# 快速上手指南

- [快速上手指南](#快速上手指南)
  - [不可绕过的步骤](#不可绕过的步骤)
  - [取出缠论元素组织策略](#取出缠论元素组织策略)
    - [CKLine-合并K线](#ckline-合并k线)
      - [CKLine\_Unit-单根K线](#ckline_unit-单根k线)
    - [bi\_list-笔管理类](#bi_list-笔管理类)
      - [CBi- 笔类](#cbi--笔类)
    - [CSegListComm-线段管理类](#cseglistcomm-线段管理类)
      - [CSeg：线段类](#cseg线段类)
    - [CZSList-中枢管理类](#czslist-中枢管理类)
      - [CZS：中枢类](#czs中枢类)
    - [CBSPointList-买卖点管理类](#cbspointlist-买卖点管理类)
      - [CBS\_Point：买卖点类](#cbs_point买卖点类)
  - [数据接入速成班](#数据接入速成班)
    - [CCommonStockApi子类实现](#ccommonstockapi子类实现)
    - [CTime](#ctime)
    - [初始化和结束](#初始化和结束)
    - [接入数据源](#接入数据源)
  - [策略实现 \& 回测](#策略实现--回测)


## 不可绕过的步骤
很多用户使用，其实不需要细看整个代码是怎么实现了，假装相信框架没BUG，通过直接提取框架计算好的缠论元素来组装策略；

但是即便如此，以下三部分建议先读README文件了解下；

- 了解CChan这个类的输入参数及格式
- 了解CChanConfig接受的配置：默认配置基本可用，关注自己想了解的即可
- 如果设计画图，了解画图的两个配置
  - plot_config：需要画什么
  - plot_para：画的每种元素单独配置

然后通过画图，可能找到一些不合理的地方（笔段中枢买卖点算错或漏算之类的），再具体去看实际实现细节或者反馈给作者。

这些README里面都有细讲。。

## 取出缠论元素组织策略
- CChan这个类里面有个变量`kl_datas`，这是一个字典，键是 KL_TYPE（即级别，具体取值参见Common/CEnum），值是 CKLine_List 类；
- CKLine_List是所有元素取值的入口，关键成员是：
  - lst: List[CKLine]：所有的合并K线
  - bi_list：CBiList 类，管理所有的笔
  - seg_list：CSegListComm 类，管理所有的线段
  - zs_list：CZSList 类，管理所有的中枢
  - bs_point_lst：CBSPointList 类，管理所有的买卖点
  - 其余大部分人可能不关注的
    - segseg_list：线段的线段
    - segzs_list：线段中枢
    - seg_bs_point_lst：线段买卖点


### CKLine-合并K线
成员包括：
- idx：第几根
- CKLine.lst可以取到所有的单根K线变量 CKLine_Unit
- fx：FX_TYPE，分形类型
- dir：方向
- pre,next：前一/后一合并K线
- high：高点
- low：低点

#### CKLine_Unit-单根K线
成员包括：
- idx：第几根
- time
- low/close/open/high
- klc：获取所属的合并K线（即CKLine）变量
- sub_kl_list: List[CKLine_Unit] 获取次级别K线列表，范围在这根K线范围内的
- sup_kl: CKLine_Unit 父级别K线（CKLine_Unit）


### bi_list-笔管理类
成员包含：
- bi_list: List[CBi]，每个元素是一笔

这个类的实现基本可以不用关注，除非你想实现自己的画笔算法

#### CBi- 笔类
成员包含：
- idx：第几笔
- dir：方向，BI_DIR类
- is_sure：是否是确定的笔
- klc_lst：List[CKLine]，该笔全部合并K线
- seg_idx：所属线段id
- parent_seg:CSeg 所属线段
- next/pre：前一/后一笔

可以关注一下这里面实现的一些关键函数：
- _high/_low
- get_first_klu/get_last_klu：获取笔第一根/最后一根K线
- get_begin_klu/get_end_klu：获取起止K线
  - 注意一下：和get_first_klu不一样的地方在于，比如下降笔，这个获取的是第一个合并K线里面high最大的K线，而不是第一个合并K线里面的第一根K线；
- get_begin_val/get_end_val：获取笔起止K线的价格
  - 比如下降笔get_begin_val就是get_begin_klu的高点


### CSegListComm-线段管理类
- lst: List[CSeg] 每一个成员是一根线段

这个类的实现基本可以不用关注，除非你想实现自己的画段算法，参照提供的几个demo，实现这个类的子类即可；

#### CSeg：线段类
成员包括：
- idx
- start_bi：起始笔
- end_bi：终止笔
- is_sure：是否已确定
- dir：方向，BI_DIR类
- zs_lst: List[CZS] 线段内中枢列表
- pre/next：前一/后一线段
- bi_list: List[CBi] 线段内笔的列表

关注的一些关键函数和CBi里面一样，都已实现同名函数，如：
- _high/_low
- get_first_klu/get_last_klu
- get_begin_klu/get_end_klu
- get_begin_val/get_end_val


### CZSList-中枢管理类
- zs_lst: List[CZS] 中枢列表


#### CZS：中枢类
成员包括：
- begin/end：起止K线CKLine_Unit
- begin_bi/end_bi：中枢内部的第一笔/最后一笔
- bi_in：进中枢的那一笔（在中枢外面）
- bi_out：出中枢的那一笔（在中枢外面，不一定存在）
- low/high：中枢的高低点
- peak_low/peak/high：中枢内所有笔的最高/最低值
- bi_lst：中枢内笔列表
- sub_zs_lst：子中枢（如果出现过中枢合并的话）


### CBSPointList-买卖点管理类
- lst：List[CBS_Point] 所有的买卖点


#### CBS_Point：买卖点类
成员包括：
- bi：所属的笔（买卖点一定在某一笔末尾）
- Klu：所在K线
- is_buy：True为买点，False为卖点
- type：List[BSP_TYPE] 买卖点类别，是个数组，比如2，3类买卖点是同一个


## 数据接入速成班
### CCommonStockApi子类实现
参考`DataAPI/BaoStockAPI.py`，实现一个类继承自`CCommonStockApi`，接受输入参数为：
- code
- k_type: KL_TYPE类型
- begin_date/end_date：能不能为None，应该是什么格式自行决定，会通过CChan类的初始化参数传进来；

并在该类里面实现一个关键方法：

`get_kl_data(self)`：该方法为一个生成器，yield 返回每一根K线信息 `CKLine_Unit`，K线类可以通过`CKLine_Unit(item_dict)`来实例化；

| 当然你也可以直接返回一个有序的数组，每个元素为`CKLine_Unit`，只不过性能可能会差一些；

```python
class C_YOUR_OWN_DATA_CLS(CCommonStockApi):
    def __init__(self, code, k_type=KL_TYPE.K_DAY, begin_date=None, end_date=None, autype=AUTYPE.QFQ):
        super(C_YOUR_OWN_DATA_CLS, self).__init__(code, k_type, begin_date, end_date, autype)

    def get_kl_data(self) -> Iterable[CKLine_Unit]:
       ...
       yield CKLine_Unit(item_dict)
```

item_dict为一个字典：
- 包含时间：必须是框架实现的CTime类
- 开收高低：必须要有
- 换手率，成交额，成交量：这三个可以没有

```python
{
    DATA_FIELD.FIELD_TIME: time,  # 必须是CTime
    DATA_FIELD.FIELD_OPEN: float(_open),  # 必填
    DATA_FIELD.FIELD_CLOSE: float(_close),  # 必填
    DATA_FIELD.FIELD_LOW: float(_low),  # 必填
    DATA_FIELD.FIELD_HIGH: float(_high),  # 必填
    DATA_FIELD.FIELD_VOLUME: float(volume),  # 可选
    DATA_FIELD.FIELD_TURNOVER: float(amount),  # 可选
    DATA_FIELD.FIELD_TURNRATE: float(turn),  # 可选
}
```

### CTime
构造`CTime(year, month, day, hour, minute)`实例即可；


### 初始化和结束
如果数据来源于其他服务，需要有初始化和结束的操作，那么需要额外重载实现两个类函数：
```python
  @classmethod
  def do_init(cls):
      ...

  @classmethod
  def do_close(cls):
      ...
```

比如baostock即需要实现login,logout操作，futu数据源需要初始化和关闭ctx操作；


### 接入数据源
最简单的方法就是把实现的类放在`./DataAPI/`目录下，然后`CChan`的`data_src`参数配置为`custom:文件名.类名`即可；


## 策略实现 & 回测
具体demo参见`stragety_demo.py`

原理就是：打开CChanConfig中的`triger_step`开关，那么CChan初始化的时候就不会做任何计算；

而手动调用CChan.step_load()，才会启动计算；
- 多少根K线就返回多少次
- 这个函数就是一个生成器：每喂一根K线后，就会计算当前K线位置的静态元素，返回当前的CChan类，可以用上文描述的方法来获取需要的元素；

回测啥的就用户自行组装了！
