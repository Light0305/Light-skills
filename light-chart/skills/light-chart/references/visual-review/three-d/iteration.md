# 三维修订只改变有理由的参数

记录 target_dimension、本次 movement_delta、must_preserve、candidate_regressions、remaining_gaps 和 next_single_change。每个字段描述看到的结果，而不是期望效果。

针对遮挡可调整一个相机参数；针对断层可修正采样或掩膜；针对光照可先固定色标和几何再换灯光。每次改变后都重查结构与保持项。把无法单独改变的耦合参数写清，不把机械“一次一项”当成科学要求。

接受时 accept_over_control 为真实判断，回归与缺口为空，下一步为空；仍有问题则保留实际描述。二次无效审阅停止当前回路，查明输入或约定问题，再由宿主安排新任务。
