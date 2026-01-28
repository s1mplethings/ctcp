#include "RunLoader.h"

#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>

RunState RunLoader::load(const QString &runsRoot) const {
    RunState state;
    if (runsRoot.isEmpty()) return state;

    QDir dir(runsRoot);
    if (!dir.exists()) return state;

    const auto runDirs = dir.entryInfoList(QDir::Dirs | QDir::NoDotAndDotDot);
    for (const auto &info : runDirs) {
        RunInfo ri;
        ri.id = info.fileName();
        ri.path = info.absoluteFilePath();
        ri.status = QStringLiteral("unknown");

        const QString eventsPath = QDir(ri.path).filePath(QStringLiteral("events.jsonl"));
        if (QFile::exists(eventsPath)) {
            ri.status = QStringLiteral("recorded");
            ri.outputs << eventsPath;
        }
        state.runs << ri;
    }

    if (!state.runs.isEmpty()) {
        state.currentRun = state.runs.first().id;
    }
    return state;
}
