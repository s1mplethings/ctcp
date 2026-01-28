#include "LayoutEngine.h"

#include <QtMath>
#include <QHash>

namespace {
struct LayoutCfg {
    QStringList phaseOrder;
    QStringList typeRows;
    double phaseGapX{700};
    double phaseOriginX{0};
    double phaseOriginY{0};
    double blockPadX{80};
    double blockPadY{80};
    double rowGapY{120};
    double colGapX{220};
    int maxColsPerRow{6};
};

QStringList arrayToStrings(const QJsonArray &arr) {
    QStringList out;
    out.reserve(arr.size());
    for (const auto &v : arr) out << v.toString();
    return out;
}

LayoutCfg parseCfg(const QJsonObject &ui) {
    LayoutCfg cfg;
    const auto layout = ui.value("layout_config").toObject();
    cfg.phaseOrder = arrayToStrings(ui.value("phase_order").toArray());
    if (cfg.phaseOrder.isEmpty()) cfg.phaseOrder = {"Docs","Core","UI","Web","Contracts","Unassigned"};
    cfg.typeRows = arrayToStrings(layout.value("type_rows").toArray());
    if (cfg.typeRows.isEmpty()) cfg.typeRows = {"Doc","Module","Contract","Gate","Run"};
    cfg.phaseGapX = layout.value("phase_gap_x").toDouble(700);
    const auto origin = layout.value("phase_origin").toObject();
    cfg.phaseOriginX = origin.value("x").toDouble(0);
    cfg.phaseOriginY = origin.value("y").toDouble(0);
    const auto pad = layout.value("block_padding").toObject();
    cfg.blockPadX = pad.value("x").toDouble(80);
    cfg.blockPadY = pad.value("y").toDouble(80);
    cfg.rowGapY = layout.value("row_gap_y").toDouble(120);
    cfg.colGapX = layout.value("col_gap_x").toDouble(220);
    cfg.maxColsPerRow = layout.value("max_cols_per_row").toInt(6);
    return cfg;
}
} // namespace

QPointF LayoutEngine::phaseOrigin(int index, const QJsonObject &config) const {
    const LayoutCfg cfg = parseCfg(config);
    return QPointF(cfg.phaseOriginX + index * cfg.phaseGapX, cfg.phaseOriginY);
}

QPointF LayoutEngine::nodePos(int col, int row, const QJsonObject &config) const {
    const LayoutCfg cfg = parseCfg(config);
    return QPointF(cfg.blockPadX + col * cfg.colGapX, cfg.blockPadY + row * cfg.rowGapY);
}

void LayoutEngine::apply(Graph &graph, const MetaGraph &meta) const {
    const LayoutCfg cfg = parseCfg(meta.ui);
    QHash<QString, int> phaseIndex;
    for (int i = 0; i < cfg.phaseOrder.size(); ++i) phaseIndex.insert(cfg.phaseOrder[i], i);

    // phase boxes origin
    QHash<QString, QPointF> phaseOriginMap;
    for (const auto &ph : meta.phases) {
        const int idx = phaseIndex.contains(ph.id) ? phaseIndex.value(ph.id) : phaseIndex.size();
        phaseOriginMap.insert(ph.id, QPointF(cfg.phaseOriginX + idx * cfg.phaseGapX, cfg.phaseOriginY));
    }

    // positions cache
    for (auto &n : graph.nodes) {
        if (meta.positions.contains(n.id)) {
            n.position = meta.positions.value(n.id);
        }
    }

    // place missing positions deterministically
    QHash<QString, int> rowColCount; // key: phase|rowType -> count
    for (auto &n : graph.nodes) {
        if (!std::isnan(n.position.x())) continue; // already has position
        const QString phase = n.phase.isEmpty() ? QStringLiteral("Unassigned") : n.phase;
        const QString type = n.type;
        const int phaseIdx = phaseIndex.contains(phase) ? phaseIndex.value(phase) : phaseIndex.size();
        QPointF origin = QPointF(cfg.phaseOriginX + phaseIdx * cfg.phaseGapX, cfg.phaseOriginY);

        int row = cfg.typeRows.indexOf(type);
        if (row < 0) row = cfg.typeRows.size();
        const QString key = phase + "|" + QString::number(row);
        int col = rowColCount.value(key, 0);
        rowColCount[key] = col + 1;
        if (col >= cfg.maxColsPerRow) {
            row += col / cfg.maxColsPerRow;
            col = col % cfg.maxColsPerRow;
        }

        QPointF local = nodePos(col, row, meta.ui);
        n.position = QPointF(origin.x() + local.x(), origin.y() + local.y());
    }
}
