# run_094 — 1.0 mm I06首项真实FE先导

仅一项由用户手动Start Queue执行的有限元先导，不是材料参数识别或双厚度信息增益验证。

- Job：SPIO_R092_T10_I06；queue_id：q_73d547c0aa8b49b2996b91247cc20616；14CPU/0GPU。
- Datacheck/Full各一次、退出0、零自动重试；原生COMPLETED_WITH_WARNINGS，软件verdict SUCCESS。
- 1601接受增量、0cutback、无负特征值/过度畸变报告；保留接触跟踪算法回退和零力矩警告。
- 原始历史/保存帧1602，标准网格241点；位移覆盖1.200000056997mm，最大载荷1969.560059N。
- 最大保存PEEQ=0.765425026<材料上界0.9。四个保存阶段的CAX4 Gauss点Jacobian为正，不能据此证明严格网格/时间步收敛。
- NUMERICAL_QUALITY=WARNING；I06_SCOREABILITY=SCOREABLE_WITH_NUMERICAL_WARNING_FOR_EXPLORATORY_COMPARISON。
- M_FREE_REQUEST_ELIGIBLE=True；第二项尚未授权、未入队、未求解。

当前只有I06材料的第二厚度响应，不能判断M_FREE配对能否被区分；载荷放大不等于新增独立本构信息。新厚度的增量/网格/接触误差界尚未建立；正式真实材料验证仍NOT_EVALUABLE。

## 数据与复算

`jobs.csv`记录参数、身份与哈希；`data/`仅包含此项已核验FE派生曲线、保存帧PEEQ最大值及全局能量。位移mm、力N、能量J；PEEQ不等于单轴真总应变。F-D严格沿用既定符号、窗口及插值，无平滑、移零、删尖峰或外推。全局塑性耗散不是区域反力贡献。

在已有NumPy和Matplotlib的Python环境运行`python reproduce.py`，可从发布CSV复算图件和标量。本次验证环境Python3.11.13、NumPy2.1.2、Matplotlib3.10.5。原始ODB/CAE/INP、私有报告、机器路径和合作方实验均未发布；公共包支持导出数据的复算，不声称独立重建完整Abaqus求解。

本次全局预算46/100，余54。求解由用户启动，Agent只通过正式queue-only注册一项和做只读后处理。当前无M_FREE执行授权，后续只能另行申请单项人工监督先导。
