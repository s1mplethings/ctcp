// Loads contract_output schemas to build contract nodes.
#pragma once

#include <QString>
#include <QList>

struct ContractSchema {
    QString id;
    QString label;
    QString schemaPath;
};

class SchemaLoader {
public:
    QList<ContractSchema> load(const QString &specsRoot) const;
};
