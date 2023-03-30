#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author  : Xiaobo Yang
@Contact : hal_42@zju.edu.cn
@Time    : 2023/3/29 16:14
@File    : cfg.py
@Software: PyCharm
@Desc    : 
"""
import os.path as osp

from alchemy_cat.py_tools import Cfg2Tune, Param2Tune

# cfg = config = Config('configs/aff_voc/base.py',
#                       'configs/patterns/crf/deeplab_crf.py',
#                       'configs/patterns/crf/crf_eval.py')
cfg = config = Cfg2Tune('configs/patterns/seg_metrics/cls_m_IoU,pra.py',
                        cfgs_update_at_parser=('configs/aff_voc/base.py',))

cfg.rslt_dir = ...

@cfg.aff.set_IL()  # noqa
def ori_cam_dir(c):
    return osp.join(c.rslt_dir, '..', '..', 'cam')  # 因为是调参配置，在上两级目录中寻找cam。

cfg.aff.ini.aff_cfg.n_iters = Param2Tune([2, 3, 4])  # noqa
