#include "ProjectScanner.h"

#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>

namespace {
QString findMarkerPath(const QDir &root) {
    const QStringList candidates = {
        root.filePath(QStringLiteral("meta/sddai_project.json")),
        root.filePath(QStringLiteral(".sddai/project.json")),
        root.filePath(QStringLiteral("sddai.project.json"))
    };
    for (const auto &p : candidates) {
        if (QFile::exists(p)) return p;
    }
    return QString();
}

struct Marker {
    bool ok{false};
    QString docs;
    QString specs;
    QString scripts;
    QString ai;
    QString runs;
};

Marker loadMarker(const QString &path) {
    Marker m;
    QFile f(path);
    if (!f.open(QIODevice::ReadOnly)) return m;
    const auto doc = QJsonDocument::fromJson(f.readAll());
    if (!doc.isObject()) return m;
    const auto obj = doc.object();
    m.docs = obj.value(QStringLiteral("docs_root")).toString();
    m.specs = obj.value(QStringLiteral("specs_root")).toString();
    m.scripts = obj.value(QStringLiteral("scripts_root")).toString();
    m.ai = obj.value(QStringLiteral("ai_context_root")).toString();
    m.runs = obj.value(QStringLiteral("runs_root")).toString();
    m.ok = true;
    return m;
}

QString strongDocs(const QDir &root) {
    const QString docsDir = root.filePath(QStringLiteral("docs"));
    if (QDir(docsDir).exists()) {
        if (QFile::exists(QDir(docsDir).filePath(QStringLiteral("00_overview.md"))) ||
            QFile::exists(QDir(docsDir).filePath(QStringLiteral("02_workflow.md")))) {
            return QDir(docsDir).absolutePath();
        }
    }
    // docs at root
    if (QFile::exists(root.filePath(QStringLiteral("00_overview.md"))) ||
        QFile::exists(root.filePath(QStringLiteral("02_workflow.md")))) {
        return root.absolutePath();
    }
    return QString();
}

QString weakDocs(const QDir &root) {
    const QString docsDir = root.filePath(QStringLiteral("docs"));
    return QDir(docsDir).exists() ? QDir(docsDir).absolutePath() : QString();
}

QString strongSpecs(const QDir &root) {
    const QString specsDir = root.filePath(QStringLiteral("specs"));
    if (QDir(specsDir).exists()) {
        if (QDir(QDir(specsDir).filePath(QStringLiteral("modules"))).exists() ||
            QDir(QDir(specsDir).filePath(QStringLiteral("contract_output"))).exists()) {
            return QDir(specsDir).absolutePath();
        }
    }
    return QString();
}

QString weakSpecs(const QDir &root) {
    const QString specDir = root.filePath(QStringLiteral("spec"));
    if (QDir(specDir).exists()) return QDir(specDir).absolutePath();
    const QString specsDir = root.filePath(QStringLiteral("specs"));
    if (QDir(specsDir).exists()) return QDir(specsDir).absolutePath();
    return QString();
}

QString optionalDir(const QDir &root, const QString &name) {
    const QString path = root.filePath(name);
    return QDir(path).exists() ? QDir(path).absolutePath() : QString();
}

struct EvalResult {
    ProjectLayout layout;
    int score{0};
    QStringList reasons;
};

EvalResult evaluateCandidate(const QString &candidatePath) {
    EvalResult res;
    res.layout.root = QDir(candidatePath).absolutePath();
    QDir root(res.layout.root);

    // Marker
    const QString markerPath = findMarkerPath(root);
    if (!markerPath.isEmpty()) {
        Marker m = loadMarker(markerPath);
        if (m.ok) {
            res.reasons << QStringLiteral("marker:%1").arg(QFileInfo(markerPath).fileName());
            res.score += 10;
            auto resolve = [&](const QString &rel) -> QString {
                if (rel.isEmpty()) return QString();
                return QDir(root.filePath(rel)).absolutePath();
            };
            res.layout.docsRoot = resolve(m.docs);
            res.layout.specsRoot = resolve(m.specs);
            res.layout.scriptsRoot = resolve(m.scripts);
            res.layout.aiContextRoot = resolve(m.ai);
            res.layout.runsRoot = resolve(m.runs);
        }
    }

    // Heuristics (only fill missing fields)
    if (res.layout.docsRoot.isEmpty()) {
        const auto d = strongDocs(root);
        if (!d.isEmpty()) { res.layout.docsRoot = d; res.score += 4; res.reasons << "docs:strong"; }
        else {
            const auto w = weakDocs(root);
            if (!w.isEmpty()) { res.layout.docsRoot = w; res.score += 2; res.reasons << "docs:weak"; }
        }
    } else {
        res.score += 4; res.reasons << "docs:marker";
    }

    if (res.layout.specsRoot.isEmpty()) {
        const auto s = strongSpecs(root);
        if (!s.isEmpty()) { res.layout.specsRoot = s; res.score += 4; res.reasons << "specs:strong"; }
        else {
            const auto w = weakSpecs(root);
            if (!w.isEmpty()) { res.layout.specsRoot = w; res.score += 1; res.reasons << "specs:weak"; }
        }
    } else {
        res.score += 4; res.reasons << "specs:marker";
    }

    if (res.layout.scriptsRoot.isEmpty()) {
        const QString scripts = optionalDir(root, QStringLiteral("scripts"));
        if (!scripts.isEmpty() && (QFile::exists(QDir(scripts).filePath(QStringLiteral("verify.ps1"))) ||
                                   QFile::exists(QDir(scripts).filePath(QStringLiteral("verify.sh"))))) {
            res.layout.scriptsRoot = scripts;
            res.score += 2;
            res.reasons << "scripts";
        }
    } else { res.score += 2; }

    if (res.layout.aiContextRoot.isEmpty()) {
        const QString ai = optionalDir(root, QStringLiteral("ai_context"));
        if (!ai.isEmpty() && (QFile::exists(QDir(ai).filePath(QStringLiteral("problem_registry.md"))) ||
                              QFile::exists(QDir(ai).filePath(QStringLiteral("decision_log.md"))))) {
            res.layout.aiContextRoot = ai;
            res.score += 2;
            res.reasons << "ai_context";
        }
    } else { res.score += 2; }

    if (res.layout.runsRoot.isEmpty()) {
        const QString runs = optionalDir(root, QStringLiteral("runs"));
        if (!runs.isEmpty()) { res.layout.runsRoot = runs; res.score += 1; res.reasons << "runs"; }
    } else { res.score += 1; }

    // Basic warnings
    if (res.layout.docsRoot.isEmpty()) res.layout.warnings << "docs root not found";
    if (res.layout.specsRoot.isEmpty()) res.layout.warnings << "specs root not found (graph edges may be missing)";

    return res;
}
} // namespace

ProjectLayout ProjectScanner::scan(const QString &rootPath) const {
    ProjectLayout finalLayout;
    QDir inputRoot(QDir(rootPath).absolutePath());
    if (!inputRoot.exists()) {
        finalLayout.warnings << QStringLiteral("Root does not exist: %1").arg(rootPath);
        return finalLayout;
    }

    QStringList candidatePaths;
    candidatePaths << inputRoot.absolutePath();
    // also immediate subdirectories (helps when user selects parent)
    const auto subdirs = inputRoot.entryInfoList(QDir::Dirs | QDir::NoDotAndDotDot);
    for (const auto &d : subdirs) candidatePaths << d.absoluteFilePath();
    // also parent (common case: exe in build/ and project在上层)
    const QString parent = inputRoot.absoluteFilePath(QStringLiteral(".."));
    if (QDir(parent).exists()) candidatePaths << QDir(parent).absolutePath();

    int bestScore = -1;
    EvalResult best;
    QList<ProjectLayout::Candidate> allCands;
    for (const auto &c : candidatePaths) {
        EvalResult eval = evaluateCandidate(c);
        ProjectLayout::Candidate cand;
        cand.path = eval.layout.root;
        cand.score = eval.score;
        cand.reasons = eval.reasons;
        allCands << cand;

        if (eval.score > bestScore) {
            bestScore = eval.score;
            best = eval;
        }
    }

    finalLayout = best.layout;
    finalLayout.candidates = allCands;

    // Relaxed recognition: if we found either docs or specs, proceed with warnings.
    const bool hasCore = !finalLayout.docsRoot.isEmpty() || !finalLayout.specsRoot.isEmpty();
    finalLayout.recognized = hasCore;
    if (!hasCore) {
        finalLayout.warnings << QStringLiteral("Project detection weak (score %1): docs/specs missing. You can still pick roots manually.").arg(bestScore);
    }
    return finalLayout;
}
