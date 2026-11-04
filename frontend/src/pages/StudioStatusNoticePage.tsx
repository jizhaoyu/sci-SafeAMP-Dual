import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { 
  Clock, 
  AlertTriangle, 
  ArrowRight, 
  FlaskConical, 
  Sparkles, 
  Bot, 
  FileSpreadsheet, 
  Compass, 
  ShieldAlert
} from 'lucide-react';

interface ModuleConfig {
  key: string;
  title: string;
  subTitle: string;
  phase: string;
  icon: any;
  accentColor: string;
  description: string;
  restorationPrerequisites: string[];
  activeAlternatives: {
    title: string;
    description: string;
    route: string;
    icon: any;
  }[];
}

const MODULE_CONFIGS: Record<string, ModuleConfig> = {
  '/screening': {
    key: 'screening',
    title: 'AMP 通量筛选工作台',
    subTitle: 'High-Throughput Antimicrobial Peptide Screening Studio',
    phase: 'P5B 阶段规划恢复中',
    icon: Compass,
    accentColor: 'indigo',
    description: '通量筛选模块正在遵循系统进化方案进行事实校准与异步队列改造。为保障科研结论的严谨性，在完成多肽真实活性基准接入前，该模块不提供虚构或伪随机预测打分。',
    restorationPrerequisites: [
      '模型事实标定：严禁使用伪哈希或未校验启发式函数生成虚假 pKd / MIC 结果',
      '实体类型隔离：已在 P1 完成架构设计，恢复后仅接收合法天然/修饰多肽序列（严格阻断小分子 SMILES）',
      '任务异步队列：需接入 P2 阶段持久化 SQLite 任务系统，支持大批量分子脱机排队与取消',
      '独立基准测试：必须在具备已知活性的 AMP 真实基准集上完成预测准确率复核'
    ],
    activeAlternatives: [
      {
        title: '药物靶点预测 (DTI Studio)',
        description: '基于 DAVIS 激酶基准（379 靶点全矩阵）开展真实模型预测',
        route: '/dti',
        icon: FlaskConical
      },
      {
        title: 'A2A 智能体协同 (Agent Studio)',
        description: '多智能体闭环搜索与自动评估，提供候选打分与演化建议',
        route: '/agent',
        icon: Bot
      }
    ]
  },
  '/helical-wheel': {
    key: 'helical-wheel',
    title: '螺旋轮与理化机制工作台',
    subTitle: 'Peptide Helical Wheel Projection & Physicochemical Mechanism Studio',
    phase: 'P5B 阶段规划恢复中',
    icon: Compass,
    accentColor: 'teal',
    description: '螺旋轮与结构机制分析模块正在进行科学算法复核。为防止残基投影角度偏差和两亲性误判，目前正根据标准 Schiffer-Edmundson 轮图投影与疏水力矩（Hydrophobic Moment）算法进行校准重构。',
    restorationPrerequisites: [
      '投影算法标定：严谨对齐 100°/残基的 α-螺旋几何投影与两亲性疏水力矩计算公式',
      '序列字符合规：集成单字母氨基酸严格校验，阻止非标准符号和误输入的化学小分子结构',
      '矢量图谱导出：支持科研出版级 SVG/PDF 矢量图及高分辨率 PNG 一键导出',
      '与分子库联动：支持从候选暂存库（Cart）一键载入多肽实体进行机制解析'
    ],
    activeAlternatives: [
      {
        title: 'A2A 智能体协同 (Agent Studio)',
        description: '直接调用智能体分析多肽活性、疏水性与两亲性打分',
        route: '/agent',
        icon: Bot
      },
      {
        title: '先导分子优化 (Evolution Studio)',
        description: '观察分子结构突变衍生与理化性质动态追踪',
        route: '/evolution',
        icon: Sparkles
      }
    ]
  },
  '/report': {
    key: 'report',
    title: '科研交付与成果报告中心',
    subTitle: 'Scientific Delivery & Comprehensive Research Report Studio',
    phase: 'P5A 阶段规划恢复中',
    icon: FileSpreadsheet,
    accentColor: 'sky',
    description: '科研交付综合报告模块正在进行学术合规治理。重构版本将提供可复现的 Supplementary 数据集导出、出版级矢量图生成以及完整计算证据指纹链（SHA-256 数据锁定）。',
    restorationPrerequisites: [
      '证据源溯源：集成 P0 阶段生成的基准冻结指纹，声明预测模型具体版本与参数',
      '缺失值如实标定：绝不填充虚假 MM-GBSA 能量数据或未经对接的假结合口袋残基',
      '科研附件生成器：支持导出符合国际学术期刊要求的 Supplementary Table (CSV/XLSX)',
      '全格式交付：提供交互式 HTML 证据卡片与结构化 Markdown 交付文档'
    ],
    activeAlternatives: [
      {
        title: '药物靶点预测 (DTI Studio)',
        description: '在 DTI 结果面板中查看并下载单次靶点结合的可信计算报告',
        route: '/dti',
        icon: FlaskConical
      },
      {
        title: '先导分子优化 (Evolution Studio)',
        description: '查看分子结构衍生、亲和力增益及演化变体列表',
        route: '/evolution',
        icon: Sparkles
      }
    ]
  }
};

export default function StudioStatusNoticePage({ overridePath }: { overridePath?: string }) {
  const location = useLocation();
  const navigate = useNavigate();
  const currentPath = overridePath || location.pathname;

  const config = MODULE_CONFIGS[currentPath] || {
    key: 'unknown',
    title: '模块状态通知',
    subTitle: 'Module Status Notice',
    phase: '规划重构中',
    icon: AlertTriangle,
    accentColor: 'slate',
    description: '您访问的工作台正在进行系统升级与科研规范化重构。',
    restorationPrerequisites: ['系统接口校验与事实校准', '前端实体类型与导航对齐'],
    activeAlternatives: [
      {
        title: '药物靶点预测 (DTI)',
        description: '返回核心靶点亲和力预测工作台',
        route: '/dti',
        icon: FlaskConical
      }
    ]
  };

  const IconComponent = config.icon;

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      {/* Status Hero Card */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden mb-6">
        <div className="p-6 sm:p-8">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-700 dark:text-slate-300 shadow-inner">
                <IconComponent size={28} />
              </div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">
                    {config.title}
                  </h1>
                  <span className="inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full font-mono font-medium bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800">
                    <Clock size={12} />
                    {config.phase}
                  </span>
                </div>
                <p className="text-xs font-mono text-slate-500 dark:text-slate-400 mt-1">
                  {config.subTitle} · 路由: {currentPath}
                </p>
              </div>
            </div>
          </div>

          {/* Description */}
          <div className="mt-6">
            <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
              {config.description}
            </p>
          </div>

          {/* Restoration Prerequisites Checklist */}
          <div className="mt-6 bg-slate-50 dark:bg-slate-850/60 rounded-xl p-5 border border-slate-200/80 dark:border-slate-800">
            <div className="flex items-center gap-2 mb-3">
              <ShieldAlert size={16} className="text-sky-600 dark:text-sky-400" />
              <h2 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider font-mono">
                工作台功能正式验收条件 (Restoration Prerequisites)
              </h2>
            </div>
            <ul className="space-y-2.5">
              {config.restorationPrerequisites.map((prereq, idx) => (
                <li key={idx} className="flex items-start gap-2.5 text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                  <span className="shrink-0 w-4 h-4 rounded-full bg-sky-100 dark:bg-sky-950 text-sky-700 dark:text-sky-400 flex items-center justify-center text-[10px] font-bold mt-0.5">
                    {idx + 1}
                  </span>
                  <span>{prereq}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Active Alternatives Recommendation */}
      <div className="mb-6">
        <h3 className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider font-mono mb-3 px-1">
          当前已通过验收的核心工作台 (Active Studios)
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {config.activeAlternatives.map((alt, idx) => {
            const AltIcon = alt.icon;
            return (
              <button
                key={idx}
                type="button"
                onClick={() => navigate(alt.route)}
                className="text-left bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 hover:border-sky-500 dark:hover:border-sky-500 hover:shadow-md transition-all group cursor-pointer"
              >
                <div className="flex items-center justify-between gap-3 mb-2">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-sky-50 dark:bg-sky-950/60 text-sky-600 dark:text-sky-400 flex items-center justify-center">
                      <AltIcon size={16} />
                    </div>
                    <span className="text-sm font-semibold text-slate-900 dark:text-slate-100 group-hover:text-sky-600 dark:group-hover:text-sky-400 transition-colors">
                      {alt.title}
                    </span>
                  </div>
                  <ArrowRight size={14} className="text-slate-400 group-hover:text-sky-600 dark:group-hover:text-sky-400 group-hover:translate-x-0.5 transition-all" />
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                  {alt.description}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Research Compliance Badge */}
      <div className="p-4 rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/30 text-center text-xs text-slate-500 dark:text-slate-400 font-mono">
        遵循阶段式研发治理方案 · 严禁未经验证的功能伪造假阳性结果 · P0-P5 梯度推进
      </div>
    </div>
  );
}
