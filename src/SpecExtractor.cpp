#include "SpecExtractor.h"

#include <QDir>
#include <QFile>
#include <QTextStream>

namespace {
QString firstHeading(const QStringList &lines) {
    for (const auto &line : lines) {
        if (line.startsWith("# ")) {
            return line.mid(2).trimmed();
        }
    }
    return QString();
}

QStringList collectListAfterHeading(const QStringList &lines, const QString &heading) {
    QStringList items;
    bool inSection = false;
    for (const auto &line : lines) {
        if (line.startsWith("## ")) {
            inSection = line.mid(3).trimmed().compare(heading, Qt::CaseInsensitive) == 0;
            continue;
        }
        if (inSection) {
            if (line.startsWith("## ")) break;
            if (line.trimmed().startsWith("- ")) {
                items << line.trimmed().mid(2).trimmed();
            }
        }
    }
    return items;
}
} // namespace

QList<ModuleSpec> SpecExtractor::load(const QString &specsRoot) const {
    QList<ModuleSpec> modules;
    QDir root(specsRoot);
    QDir modulesDir(root.filePath("modules"));
    if (!modulesDir.exists()) return modules;

    const auto moduleDirs = modulesDir.entryInfoList(QDir::Dirs | QDir::NoDotAndDotDot);
    for (const auto &entry : moduleDirs) {
        const QString specPath = QDir(entry.absoluteFilePath()).filePath("spec.md");
        QFile f(specPath);
        if (!f.exists()) continue;
        if (!f.open(QIODevice::ReadOnly | QIODevice::Text)) continue;
        QTextStream in(&f);
        QStringList lines;
        while (!in.atEnd()) lines << in.readLine();

        ModuleSpec ms;
        ms.id = entry.fileName();
        ms.path = specPath;
        ms.label = firstHeading(lines);
        ms.inputs = collectListAfterHeading(lines, QStringLiteral("Inputs"));
        ms.outputs = collectListAfterHeading(lines, QStringLiteral("Outputs"));
        ms.verifies = collectListAfterHeading(lines, QStringLiteral("Acceptance Criteria"));
        ms.traceLinks = collectListAfterHeading(lines, QStringLiteral("Trace Links"));
        modules << ms;
    }
    return modules;
}
