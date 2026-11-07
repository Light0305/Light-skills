# 连续场、缺失域与三维图

先确定输入含义：规则/不规则间距的网格、三角网格、点云、空间轨迹、切片体域还是明确给出的解析函数。二维矩阵不是自动意义上的空间地形，矩阵索引也不自动是物理坐标。

本地 CF NetCDF 可直接进入 `figure_job.prepare_job({"climate":"source.nc"}, spec)`，也可调用 `field_data.prepare_netcdf_field(path, chart)` 取得 `.field`（直接传 `scalar_field`）、`.table` 和 `.report`。公开接口负责读取、解码、选择、转置与坐标配对，绘图任务无需重写这些步骤。`chart` 例如：

```json
{"intent":"scalar_field","variable":"temperature","x":"lon","y":"lat","time":"time",
 "isel":{"level":0},"coordinate_ranges":{"lat":[-60,60]},
 "reduce":{"operation":"mean","dimension":"time","ranges":[["2000-01-01","2009-12-31"]],
           "weighting":"equal_samples","missing":"skip"},"limits":[250,310]}
```

字段名、层索引、时间段和色限必须来自实际任务。所有额外维度（包括单层）需显式 `isel`；二维单时刻则显式选择时间索引，不默认均值。`difference_of_means` 需两个 `ranges` 和 `direction="second_minus_first"`，均值始终是已声明的等观测权，不冒充按持续时间/面积加权。`missing=skip` 保留逐格有效数；`propagate` 让存在缺值的归约格保持 NA，全缺格不变零。可选 `value_transform={"scale":1,"offset":-273.15,"unit":"degC"}` 在归约前明确转换，原单位和转换被记录；无单位时必须显式补 `value_unit/x_unit/y_unit`，不凭变量名猜测。

同一 NetCDF 可在多面板声明不同变量/时间归约，也可与 CSV 面板混合进入原证据链。只有准备后的二维格点进入 profiler；原时间×空间立方体不展成长表。文件哈希、CF打包信息、实际 reader engine、原轴、时间选取、逐格有效数和物理单位见 `.report`/决策 `input_preparation`。同文件派生视图采用保守文件级 ancestry，不能被称为独立验证。

当前仅支持实数规则/非均匀一维直角格网，保留原经纬度范围，不自动改成 −180…180、重投影或插值。曲线网格、未知层/变量、不可解码日历、缺 reader 依赖会返回 `needs_resolution`，不能算 `prepared`。`xarray` 和对应文件 reader 是可选依赖；旧 CSV 路径无需导入 xarray。基础环境可用 SciPy 读取 NetCDF3，HDF5 NetCDF 需可用 `h5netcdf`/`netcdf4`（也可显式 `engine`），不自动安装或修改全局环境。

`scripts/field_tools.py` 的 `grid_field(x, y, z, limits=..., center=...)` 面向**有序网格中心值**。它要求 `z.shape == (len(y), len(x))`，拒绝猜测转置、重复/非单调坐标和无穷值；下降坐标会与相应的数值行列一起反转，缺失域保持 NA，不做插补或曲面拟合。

`scalar_field()` 使用真实坐标的 pcolormesh，非均匀间距不会被压成等宽像素；NA 有专门颜色。图的边缘按相邻中心间距的一半外推，这是中心值网格的显示约定，不是测量域的新数据。有限元节点、原始三角面片或明确边界的数据需用其本来的网格与边界。

`field_surface()` 保留每个网格顶点（显式 rcount/ccount），避免 Matplotlib 默认网格降采样。密集面可以栅格化，轴与文字保持矢量；大网格的细化、渲染代价或有依据的降采样需单独说明。相机、投影、盒子比例是显示参数，不能修改真实高度来伪造起伏。

二维与三维定量视图共享同一 `Normalize` 和色标，不把同色解释成不同的值。色彩表示数据时关闭额外光照着色，以免表面照明混淆色标；材料照明图另读[材质与光照](visual-review/three-d/light-and-material.md)，并明确颜色不是数据量。

三维常有遮挡：需要比较精确峰谷或不确定性时联用平面图、等高线或剖面。对照参考要分别检查：表示类型、拓扑、可见极值、相机、占据率、轴/色标/图例可读性。源 RNAGenScape “gray patches” 是灰色覆盖，不是数据中真的缺口，不能混淆为缺失域。

[Light-Science 三维入口](visual-review/three-d/route.md)保留进一步的曲面、体域、几何、轨迹和修订选择细则。本包不会仅因“高级感”把二维数据变三维，也不会用图像生成补造科研场。

需要严格候选比较或控制稿替换时，使用 [review-cycle 的显式三维接口](review-cycle.md)：真实参考/控制图、最终 PDF、实际 routed inserts、几何资源快照和原 scorecard 一起绑定不可变 stage。科学核对需分别覆盖坐标/单位、真实几何与边界/连通性、相机遮挡、可见极值及剖切互证；图像审阅的 topology 分数不能代替真实面片拓扑或生物验证。换布局先建立科学合格的新基线，再固定控制稿修订，不能把不同面板结构的占据率变化硬当作改进。

`scripts/raster_diagnostics.py` 按需报告尺寸、非白区域和同网格像素差异，不报告 topology、camera 或 color semantics 分数，也不进行综合排名。它不能核对真实几何、相机标定、科学含义或文字可读性；最终仍以数据核对和实际读图为准。见[像素诊断](visual-review/raster-diagnostics.md)。

可运行示例：`assets/examples/fields_and_tables.py` 输出明确标为解析演示的同场二维/三维视图，提供公式、非均匀网格与缺失域 NPZ。它用于验证数据与显示映射，不能拿来宣称对真实实验的效果。

复杂组合可用 composition 的 projection="3d"，实测三维坐标装饰的最终边界，搭配二维位置图、剖面和共有色标。布局不改变相机/高度；相机候选要实际查看，优先保留决定性峰谷或空腔，同时用伴随二维视图说明不可避免的遮挡。

`volume_isosurface(ax, volume, spacing=(dz,dy,dx), level=..., origin=(z0,y0,x0))` 面向真正三维体素，不限于单值高度场。使用 marching cubes 的等值面线性插值，step_size=1；不平滑、填洞、删除小连通域或减面。保留三角面/顶点哈希、阈值、体素间距和触及裁剪边界的记录。恒定材质色不是体素强度；等值面不是经过验证的生物分割或细胞计数。未知标定只能使用体素单位，不能凭观感补 µm。

`image_layout.orthogonal_slice(volume, plane="xz", index=i, spacing=(dz,dy,dx), origin=(z0,y0,x0))` 仅从明确 ZYX 体素提取原切片，返回原值副本、行列轴、索引/坐标和来源哈希。科学多通道需先显式选择，不将四维原始强度猜为 RGB。返回的 `pixels`、`pixel_size` 与 `center_origin` 可传给 `image_panel()`；同一体数据的切片和等值面使用一致的首体素中心。

`image_panel()` 的 `pixel_size` 可为标量或 `(row_spacing,col_spacing)`，保真实长宽比。旧调用默认保留裁剪局部边界零；显式 `center_origin=(row0,col0)` 才使用未裁剪源图首像素中心坐标，边界为 `origin + (source_index−0.5)×spacing`。`image_plate()` 的 `equal_unit_group` 让不同方向切片保持相同物理倍率；`equal_pixel_group` 保留方形像素的旧语义。`link_roi()` 核对来源、校准和原点，框定原始半开裁剪范围，不重采样或挑选“漂亮”区域。
