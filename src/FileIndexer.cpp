#include "FileIndexer.h"

#include <QDirIterator>

QStringList FileIndexer::index(const ProjectLayout &layout) const {
    QStringList files;
    const QStringList roots = {
        layout.docsRoot, layout.specsRoot, layout.scriptsRoot, layout.aiContextRoot
    };
    for (const auto &root : roots) {
        if (root.isEmpty()) continue;
        QDirIterator it(root, QDir::Files, QDirIterator::Subdirectories);
        while (it.hasNext()) files << it.next();
    }
    return files;
}
