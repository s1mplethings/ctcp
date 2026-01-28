// Builds Graph JSON by merging specs, contracts, meta, and runtime state.
#pragma once

#include "GraphTypes.h"
#include "MetaStore.h"
#include "ProjectScanner.h"
#include "RunLoader.h"
#include "SchemaLoader.h"
#include "SpecExtractor.h"

class GraphBuilder {
public:
    Graph build(const ProjectLayout &layout,
                const QList<ModuleSpec> &modules,
                const QList<ContractSchema> &contracts,
                const MetaGraph &meta,
                const RunState &runs) const;
};
