// LayoutEngine: deterministic preset positions for Pipeline view
#pragma once

#include "GraphTypes.h"
#include "MetaStore.h"

class LayoutEngine {
public:
    void apply(Graph &graph, const MetaGraph &meta) const;

private:
    QPointF phaseOrigin(int index, const QJsonObject &config) const;
    QPointF nodePos(int col, int row, const QJsonObject &cfg) const;
};
