// Loads runtime info from runs directory (lightweight MVP).
#pragma once

#include <QString>
#include <QStringList>
#include <QList>

struct RunInfo {
    QString id;
    QString status;
    QString startTime;
    QString path;
    QStringList outputs;
};

struct RunState {
    QList<RunInfo> runs;
    QString currentRun;
};

class RunLoader {
public:
    RunState load(const QString &runsRoot) const;
};
