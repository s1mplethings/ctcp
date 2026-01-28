// DocPreviewer: open/read files for double-click preview
#pragma once

#include <QObject>
#include <QString>

class DocPreviewer : public QObject {
    Q_OBJECT
public:
    explicit DocPreviewer(QObject *parent = nullptr);

    Q_INVOKABLE QString readFile(const QString &path) const;
};
