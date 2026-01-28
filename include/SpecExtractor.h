// Extracts lightweight info from specs/modules/<module>/spec.md
#pragma once

#include <QString>
#include <QStringList>
#include <QList>

struct ModuleSpec {
    QString id;
    QString label;
    QString path;
    QString phase;           // optional (from meta later)
    QStringList inputs;      // contract ids or free text
    QStringList outputs;     // contract ids or free text
    QStringList verifies;    // contract ids or gates
    QStringList traceLinks;  // docs references
};

class SpecExtractor {
public:
    QList<ModuleSpec> load(const QString &specsRoot) const;
};
