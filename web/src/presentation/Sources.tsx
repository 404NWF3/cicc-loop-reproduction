import { Link } from 'react-router-dom';
const root = '/presentation/';
export function Sources() {
  return (
    <div className="deck-notes">
      <h3>研究资料</h3>
      <p>
        主体内容依据用户提供的《案例 G：中金 AI
        因子挖掘案例分析》。所引中金数据为材料转述的历史回测，不等于独立复核或实盘。
      </p>
      <a href="https://mp.weixin.qq.com/s/hrKdYATh_9rdASVAdjGymg" target="_blank" rel="noreferrer">
        材料所引中金报告 ↗
      </a>
      <a href="https://doi.org/10.1093/rfs/hhaa009" target="_blank" rel="noreferrer">
        Gu, Kelly & Xiu (2020) ↗
      </a>
      <Link to="/experiments">本地 v2 实验、协议与留出结果 ↗</Link>
      <a
        href="https://github.com/yumoxu/stocknet-dataset/tree/330708b5ddc359961078bef469f43f48992fd6e4"
        target="_blank"
        rel="noreferrer"
      >
        历史价量数据：StockNet 固定版本 ↗
      </a>
      <h3>图像来源</h3>
      <p>照片均为背景或概念配图，不展示中金内部场景。图表按注明来源重绘。</p>
      <a
        href="https://commons.wikimedia.org/wiki/File:Pudong_Shanghai_November_2017_panorama.jpg"
        target="_blank"
        rel="noreferrer"
      >
        上海：King of Hearts · CC BY-SA 4.0 ↗
      </a>
      <a
        href="https://commons.wikimedia.org/wiki/File:New_York_Stock_Exchange_trading_floor_on_Wall_Street,_New_York,_New_York_LCCN2011634218.tif"
        target="_blank"
        rel="noreferrer"
      >
        NYSE：Carol M. Highsmith · 公有领域 ↗
      </a>
      <a
        href="https://commons.wikimedia.org/wiki/File:Server_racks_near_the_GBAR_experiment.jpg"
        target="_blank"
        rel="noreferrer"
      >
        CERN 机柜：Unnerving duck · CC BY-SA 4.0 ↗
      </a>
      <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noreferrer">
        CC BY-SA 4.0 授权说明 ↗
      </a>
      <p>
        照片原文件未修改，页面仅作容器裁切。字体使用 Noto，遵循 SIL Open Font
        License。参考网页提供排版灵感，未复制图文。
      </p>
      <a href={`${root}sources.json`}>完整图像清单与原文件地址 ↗</a>
      <h3>版式与许可</h3>
      <p>采用 guizang-ppt-skill 的 Style A「靛蓝瓷」，由本项目适配为研究演示。</p>
      <a href="/presentation/source/index.html" target="_blank" rel="noreferrer">
        演示源码与 AGPL-3.0 许可 ↗
      </a>
    </div>
  );
}
