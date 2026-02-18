#include "MainWindow.h"

#include "Bridge.h"
#include "sddai_bridge.h"
#include "details_window.h"

#include <QAction>
#include <QDir>
#include <QCoreApplication>
#include <QFileDialog>
#include <QFileSystemModel>
#include <QDockWidget>
#include <QKeySequence>
#include <QLabel>
#include <QMenuBar>
#include <QSplitter>
#include <QStatusBar>
#include <QTreeView>
#include <QTimer>
#include <QWebChannel>
#include <QWebEngineView>
#include <QFile>
#include <QStyle>

MainWindow::MainWindow(QWidget *parent) : QMainWindow(parent) {
    createUi();
    createMenu();
    setWindowTitle(QStringLiteral("SDDAI GUI (QtWebEngine + Graph Spider)"));
    resize(1200, 720);

    // Auto-open: prefer project root (one level above exe) to avoid landing in build/.
    const QString exeDir = QCoreApplication::applicationDirPath();
    const QString candidate = QDir(exeDir).absoluteFilePath(QStringLiteral(".."));
    openProject(QDir(candidate).absolutePath());
}

MainWindow::~MainWindow() = default;

void MainWindow::createUi() {
    bridge_ = new Bridge(this);
    connect(bridge_, &Bridge::toast, this, &MainWindow::handleToast);
    exposedBridge_ = new SddaiBridge(bridge_, this);

    auto splitter = new QSplitter(this);
    fsModel_ = new QFileSystemModel(this);
    fsModel_->setRootPath(QDir::currentPath());
    fsModel_->setFilter(QDir::NoDotAndDotDot | QDir::AllDirs | QDir::Files);

    tree_ = new QTreeView(splitter);
    tree_->setModel(fsModel_);
    tree_->setColumnWidth(0, 200);
    tree_->setMaximumWidth(280);
    tree_->setMinimumWidth(180);
    connect(tree_, &QTreeView::doubleClicked, [this](const QModelIndex &idx) {
        bridge_->openFile(fsModel_->filePath(idx));
    });

    webView_ = new QWebEngineView(splitter);
    splitter->setSizes(QList<int>{220, 980});
    splitter->setStretchFactor(1, 1);
    splitter->setStretchFactor(0, 0);
    setCentralWidget(splitter);

    // WebChannel hookup (main graph view)
    auto channel = new QWebChannel(webView_);
    channel->registerObject(QStringLiteral("bridge"), exposedBridge_);
    webView_->page()->setWebChannel(channel);
    webView_->setUrl(QUrl(QStringLiteral("qrc:/web/graph_spider/index.html")));

    // Details dock with independent WebView
    // NOTE: QWebEngineView can go blank when a QDockWidget is floated (re-parented to a new top-level window).
    // Provide a stable dedicated window instead (see View -> Open Details Window).
    detailsDock_ = new QDockWidget(tr("Details"), this);
    detailsDock_->setFeatures(QDockWidget::DockWidgetMovable | QDockWidget::DockWidgetClosable);
    detailsDock_->setMinimumWidth(320);
    detailsView_ = new QWebEngineView(detailsDock_);
    auto channel2 = new QWebChannel(detailsView_->page());
    channel2->registerObject(QStringLiteral("bridge"), exposedBridge_);
    detailsView_->page()->setWebChannel(channel2);
    detailsView_->setUrl(QUrl(QStringLiteral("qrc:/web/graph_spider/details.html")));
    detailsDock_->setWidget(detailsView_);
    addDockWidget(Qt::RightDockWidgetArea, detailsDock_);
    detailsDock_->resize(380, 720);
    detailsDock_->show();

    // Defensive reload hooks (keeps details view alive when layout changes)
    connect(detailsDock_, &QDockWidget::visibilityChanged, this, [this](bool vis) {
        if (vis && detailsView_) QTimer::singleShot(0, detailsView_, [this]() { detailsView_->reload(); });
    });

    statusBar()->showMessage(QStringLiteral("Ready"));
    projectLabel_ = new QLabel(tr("No project loaded"), this);
    statusBar()->addPermanentWidget(projectLabel_);
}

void MainWindow::createMenu() {
    auto fileMenu = menuBar()->addMenu(tr("&File"));
    auto openAct = fileMenu->addAction(tr("Open Project..."));
    openAct->setShortcut(QKeySequence::Open);
    connect(openAct, &QAction::triggered, this, &MainWindow::chooseProject);

    auto reloadAct = fileMenu->addAction(tr("Reload Graph"));
    connect(reloadAct, &QAction::triggered, [this]() {
        const QString root = fsModel_->rootPath();
        if (!root.isEmpty()) bridge_->openProject(root);
    });

    fileMenu->addSeparator();
    auto quitAct = fileMenu->addAction(tr("Quit"));
    quitAct->setShortcut(QKeySequence::Quit);
    connect(quitAct, &QAction::triggered, this, &QWidget::close);

    auto viewMenu = menuBar()->addMenu(tr("&View"));
    auto toggleDetails = viewMenu->addAction(tr("Toggle Details"));
    toggleDetails->setCheckable(true);
    toggleDetails->setChecked(true);
    connect(toggleDetails, &QAction::triggered, [this, toggleDetails]() {
        if (!detailsDock_) return;
        detailsDock_->setVisible(!detailsDock_->isVisible());
        toggleDetails->setChecked(detailsDock_->isVisible());
    });

    auto openDetailsWin = viewMenu->addAction(tr("Open Details Window"));
    connect(openDetailsWin, &QAction::triggered, this, &MainWindow::openDetailsWindow);
}

void MainWindow::openDetailsWindow() {
    if (!detailsWindow_) {
        detailsWindow_ = new DetailsWindow(exposedBridge_, this);
        detailsWindow_->setAttribute(Qt::WA_DeleteOnClose, false);
    }
    detailsWindow_->show();
    detailsWindow_->raise();
    detailsWindow_->activateWindow();
    detailsWindow_->reloadPage();
}

void MainWindow::chooseProject() {
    const QString dir = QFileDialog::getExistingDirectory(this, tr("Open Project"), QString());
    if (!dir.isEmpty()) {
        openProject(dir);
    }
}

void MainWindow::openProject(const QString &path) {
    const auto idx = fsModel_->setRootPath(path);
    tree_->setRootIndex(idx);
    if (exposedBridge_) exposedBridge_->setProjectRoot(path);
    if (bridge_->openProject(path)) {
        statusBar()->showMessage(tr("Loaded project: %1").arg(path), 3000);
        projectLabel_->setText(QDir(path).dirName());
    } else {
        statusBar()->showMessage(tr("Failed to load project"), 5000);
    }
}

void MainWindow::handleToast(const QString &msg) {
    statusBar()->showMessage(msg, 5000);
}
