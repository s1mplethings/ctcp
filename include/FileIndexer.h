// Basic file indexer (placeholder for QFileSystemWatcher integration).
#pragma once

#include "ProjectScanner.h"
#include <QStringList>

class FileIndexer {
public:
    QStringList index(const ProjectLayout &layout) const;
};
