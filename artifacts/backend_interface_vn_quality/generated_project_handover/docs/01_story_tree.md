# 01 剧情树

## 主线节点
- N00_intro 归乡开场
- N10_archive 旧校舍档案室
- N20_cafe 夜间咖啡馆
- N30_confession 暴雨告白

## 结局节点
- E01_truth 真相结局
- E02_silence 沉默结局

## 分支依赖
- N00_intro -> N10_archive / N20_cafe
- N10_archive -> N30_confession
- N20_cafe -> N30_confession
- N30_confession -> E01_truth / E02_silence
