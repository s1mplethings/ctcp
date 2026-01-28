#include "SchemaLoader.h"

#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTextStream>

QList<ContractSchema> SchemaLoader::load(const QString &specsRoot) const {
    QList<ContractSchema> schemas;
    QDir root(specsRoot);
    QDir contractsDir(root.filePath("contract_output"));
    const auto files = contractsDir.entryInfoList(QStringList() << "*.schema.json", QDir::Files);
    for (const auto &file : files) {
        QFile f(file.absoluteFilePath());
        if (!f.open(QIODevice::ReadOnly)) continue;
        const auto json = QJsonDocument::fromJson(f.readAll());
        ContractSchema cs;
        cs.id = file.baseName(); // e.g., graph.schema.json -> graph
        cs.schemaPath = file.absoluteFilePath();
        if (json.isObject()) {
            cs.label = json.object().value(QStringLiteral("title")).toString(cs.id);
        } else {
            cs.label = cs.id;
        }
        schemas << cs;
    }
    return schemas;
}
