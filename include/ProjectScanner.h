// Scans a project directory for SDDAI layout hints.
#pragma once

#include <QString>
#include <QStringList>
#include <QDir>
#include <QList>

struct ProjectLayout {
    bool recognized{false};
    QString root;
    QString docsRoot;
    QString specsRoot;
    QString scriptsRoot;
    QString aiContextRoot;
    QString runsRoot;
    QStringList warnings;

    struct Candidate {
        QString path;
        int score{0};
        QStringList reasons;
    };
    QList<Candidate> candidates;
};

class ProjectScanner {
public:
    ProjectLayout scan(const QString &rootPath) const;
};
