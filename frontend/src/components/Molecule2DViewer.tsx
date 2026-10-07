import React, { useMemo, useState } from 'react';
import { Maximize2, X } from 'lucide-react';
import { 
  parseSmilesTo2D 
} from '../utils/cheminformatics';

interface Props {
  smiles: string;
  name?: string;
  width?: number;
  height?: number;
  showExpandButton?: boolean;
}

export const Molecule2DViewer: React.FC<Props> = ({
  smiles,
  name,
  width = 240,
  height = 140,
  showExpandButton = true,
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const { nodes, bonds, viewBox } = useMemo(() => {
    const parsed = parseSmilesTo2D(smiles);
    if (parsed.nodes.length === 0) {
      return { nodes: [], bonds: [], viewBox: '0 0 100 100' };
    }

    // Compute bounding box
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;

    for (const node of parsed.nodes) {
      if (node.x < minX) minX = node.x;
      if (node.x > maxX) maxX = node.x;
      if (node.y < minY) minY = node.y;
      if (node.y > maxY) maxY = node.y;
    }

    const pad = 24;
    const boxW = Math.max(80, maxX - minX + pad * 2);
    const boxH = Math.max(60, maxY - minY + pad * 2);

    // Normalize coordinates so minX, minY is at pad
    const shiftedNodes = parsed.nodes.map(n => ({
      ...n,
      x: n.x - minX + pad,
      y: n.y - minY + pad,
    }));

    return {
      nodes: shiftedNodes,
      bonds: parsed.bonds,
      viewBox: `0 0 ${boxW} ${boxH}`,
    };
  }, [smiles]);

  const renderSVGContent = (fontSize = 9) => (
    <>
      {/* Chemical Bonds */}
      <g strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="stroke-slate-600 dark:stroke-slate-300">
        {bonds.map((bond, idx) => {
          const a1 = nodes[bond.from];
          const a2 = nodes[bond.to];
          if (!a1 || !a2) return null;

          if (bond.order === 2) {
            // Double bond: draw offset parallel lines
            const dx = a2.x - a1.x;
            const dy = a2.y - a1.y;
            const len = Math.sqrt(dx * dx + dy * dy) || 1;
            const ox = (-dy / len) * 2;
            const oy = (dx / len) * 2;

            return (
              <g key={`bond-${idx}`}>
                <line x1={a1.x + ox} y1={a1.y + oy} x2={a2.x + ox} y2={a2.y + oy} />
                <line x1={a1.x - ox} y1={a1.y - oy} x2={a2.x - ox} y2={a2.y - oy} />
              </g>
            );
          }

          if (bond.order === 1.5) {
            // Aromatic bond: main line + dashed inner line
            const dx = a2.x - a1.x;
            const dy = a2.y - a1.y;
            const len = Math.sqrt(dx * dx + dy * dy) || 1;
            const ox = (-dy / len) * 2.5;
            const oy = (dx / len) * 2.5;

            return (
              <g key={`bond-${idx}`}>
                <line x1={a1.x} y1={a1.y} x2={a2.x} y2={a2.y} />
                <line
                  x1={a1.x + ox}
                  y1={a1.y + oy}
                  x2={a2.x + ox}
                  y2={a2.y + oy}
                  strokeDasharray="2,2"
                  strokeWidth="1.5"
                  className="stroke-slate-400 dark:stroke-slate-400"
                />
              </g>
            );
          }

          // Single bond
          return <line key={`bond-${idx}`} x1={a1.x} y1={a1.y} x2={a2.x} y2={a2.y} />;
        })}
      </g>

      {/* Atoms */}
      <g>
        {nodes.map(node => {
          if (!node.isHetero) {
            // Carbon is drawn as vertex only (no label in standard skeletal formula)
            return null;
          }

          return (
            <g key={`atom-${node.id}`}>
              {/* Background pill to mask bonds behind atom letter */}
              <circle
                cx={node.x}
                cy={node.y}
                r={fontSize * 0.8}
                className="fill-white dark:fill-slate-900"
              />
              <text
                x={node.x}
                y={node.y + fontSize * 0.35}
                textAnchor="middle"
                fontSize={fontSize}
                fontWeight="bold"
                fontFamily="ui-sans-serif, system-ui, sans-serif"
                fill={node.color}
              >
                {node.symbol}
              </text>
            </g>
          );
        })}
      </g>
    </>
  );

  return (
    <div className="relative group/mol inline-block">
      <div
        className="rounded-lg bg-slate-50/80 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 p-1.5 flex items-center justify-center overflow-hidden transition-all hover:border-blue-400 dark:hover:border-blue-600 shadow-2xs"
        style={{ width, height }}
      >
        <svg
          viewBox={viewBox}
          className="w-full h-full max-h-full max-w-full drop-shadow-2xs select-none"
          preserveAspectRatio="xMidYMid meet"
        >
          {renderSVGContent(9)}
        </svg>
      </div>

      {showExpandButton && (
        <button
          type="button"
          onClick={() => setIsModalOpen(true)}
          className="absolute top-1.5 right-1.5 p-1 rounded bg-white/90 dark:bg-slate-900/90 text-slate-500 hover:text-blue-600 dark:hover:text-blue-400 border border-slate-200 dark:border-slate-700 opacity-0 group-hover/mol:opacity-100 transition-opacity shadow-xs"
          title="放大查看 2D 分子拓扑骨架"
          aria-label="放大查看 2D 分子拓扑骨架"
        >
          <Maximize2 size={12} />
        </button>
      )}

      {/* Modal Dialog for enlarged structure */}
      {isModalOpen && (
        <div
          className="fixed inset-0 z-[120] flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in duration-150"
          role="dialog"
          aria-modal="true"
        >
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl w-full max-w-xl p-6 flex flex-col space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  {name || '分子 2D 骨架拓扑结构图'}
                </h3>
                <span className="text-[11px] font-mono text-slate-400 break-all select-all block mt-0.5">
                  {smiles}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-md"
                aria-label="关闭"
              >
                <X size={18} />
              </button>
            </div>

            <div className="w-full h-72 bg-slate-50 dark:bg-slate-950 rounded-xl border border-slate-100 dark:border-slate-800 p-4 flex items-center justify-center">
              <svg
                viewBox={viewBox}
                className="w-full h-full max-h-full max-w-full"
                preserveAspectRatio="xMidYMid meet"
              >
                {renderSVGContent(12)}
              </svg>
            </div>

            <div className="flex items-center justify-between text-xs text-slate-500 pt-2 border-t border-slate-100 dark:border-slate-800">
              <span>包含 {nodes.length} 个重原子 · {bonds.length} 根化学键</span>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-200 font-medium text-xs"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
