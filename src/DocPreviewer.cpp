#include "DocPreviewer.h"

#include <QFile>
#include <QTextStream>

DocPreviewer::DocPreviewer(QObject *parent) : QObject(parent) {}

QString DocPreviewer::readFile(const QString &path) const {
    QFile f(path);
    if (!f.open(QIODevice::ReadOnly | QIODevice::Text)) return QString();
    QTextStream ts(&f);
    return ts.readAll();
}
