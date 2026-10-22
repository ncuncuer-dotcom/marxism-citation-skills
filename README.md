# 马理论论文引文检索 Skill 合集

**8套文献、36卷，一个统一检索入口。** 根据论文题目、摘要、论点或关键词，在自己准备的PDF中寻找候选原话，回读上下文，核对文集、卷次、篇名和页码。

合集包含统一入口 `marxism-citation-research` 及8套独立Skill。整个合集可以作为一个Skill安装；也可以只安装需要的独立目录。

只分发指令和本地工具，不包含原书PDF、全文提取数据、OCR识别结果、个人路径或全文索引。每位使用者用自己的文献建立索引。

## 包含哪些文集

| 文集 | 卷次 | 统一入口ID | 独立Skill及安装说明 |
| --- | --- | --- | --- |
| 《马克思恩格斯文集》 | 1—10 | `marx-engels` | [marx-engels-wenji-research](skills/marx-engels-wenji-research/README.md) |
| 《毛泽东文集》 | 1—8 | `mao` | [mao-wenji-research](skills/mao-wenji-research/README.md) |
| 《邓小平文选》 | 1—3 | `deng` | [deng-xiaoping-wenxuan-research](skills/deng-xiaoping-wenxuan-research/README.md) |
| 《江泽民文选》 | 1—3 | `jiang` | [jiang-zemin-wenxuan-research](skills/jiang-zemin-wenxuan-research/README.md) |
| 《胡锦涛文选》 | 1—3 | `hu` | [hu-jintao-wenxuan-research](skills/hu-jintao-wenxuan-research/README.md) |
| 《习近平谈治国理政》 | 1—5 | `xi-governance` | [xi-governance-research](skills/xi-governance-research/README.md) |
| 《习近平党建文选》 | 1—2 | `xi-dangjian` | [xi-dangjian-wenxuan-research](skills/xi-dangjian-wenxuan-research/README.md) |
| 《习近平著作选读》 | 1—2 | `xi-xuandu` | [xi-zhuzuo-xuandu-research](skills/xi-zhuzuo-xuandu-research/README.md) |

36卷是支持范围，不代表新安装后已经具备36卷原文。实际覆盖取决于本地索引，状态检查会报告缺失文集和卷次。

## 安装整个合集

1. 下载并解压合集ZIP，将包含本README、`SKILL.md`和`skills/`的顶层文件夹命名为 `marxism-citation-research`。
2. 把完整文件夹放入支持的Skill目录，例如 `~/.codex/skills/marxism-citation-research/`。保留整个目录结构。没有单独安装子Skill也可使用统一入口。
3. 在顶层文件夹中安装依赖并检查状态：

   ```bash
   python3 -m pip install -r requirements.txt
   python3 scripts/research.py --status
   ```

   需要Python 3.9+、支持FTS5的SQLite。唯一第三方依赖PyMuPDF用于PDF提取和渲染。Windows若使用`python`，将示例中的`python3`替换为`python`。这些命令在合集顶层运行；也可以使用脚本的绝对路径。

4. 根据自己的PDF建立索引。例如：

   ```bash
   python3 skills/jiang-zemin-wenxuan-research/scripts/rebuild_index.py --source-dir "自己的江泽民文选PDF目录"
   python3 skills/xi-dangjian-wenxuan-research/scripts/rebuild_index.py --source-dir "自己的党建文选PDF目录"
   python3 scripts/research.py --status
   ```

   每套单独建立、更新索引。默认要求该套卷次完整；仅有部分卷时显式加`--allow-partial`，引用结果会说明实际范围。文件名无法识别时用`--manifest`映射，格式见对应独立Skill的README。不要把多套图书混在一个目录直接建立单套索引。

5. 开启新对话使用：

   > 用 marxism-citation-research，根据论文主题“调查研究与认识方法”，在相关文集中找原话，附上下文和准确出处，并说明实际检索范围。

也可以明确要求“跨8套文集检索”或指定其中几套。原来的8个独立Skill名依然可以按各自安装情况使用。

## 扫描PDF怎么处理

需要可搜索文字层；扫描件须先OCR。胡锦涛文选、习近平著作选读的子Skill附带macOS Apple Vision辅助脚本，在本机处理、保留原PDF，并校验识别结果的源文件指纹与完整页序。详细操作见各自README。其他系统也可先用自己的OCR工具生成带文字层PDF。

OCR结果只用于找到候选。即使识别顺利完成，也可能出现错字、漏字、页眉混入、标点或行序错误；引用前仍须查看原页。

## 统一检索与回读

```bash
# 检查8套索引及实际覆盖
python3 scripts/research.py --status

# 默认检索全部可用套；每套最多3个候选
python3 scripts/research.py 调查 研究 实际 --limit 3

# 指定两套
python3 scripts/research.py 改革 发展 --collection deng --collection jiang --limit 4

# 回读某一文集的原页及相邻页
python3 scripts/research.py --page xi-xuandu:2:30 --context 1

# 输出原页图，供图片查看工具核对
python3 scripts/research.py --page xi-xuandu:2:30 --render work/page.png

# 查看单套书签导航；无书签时可能没有输出
python3 scripts/research.py --catalogue --collection jiang
```

定位为`文集ID:卷:PDF页序`，PDF页序从1起算，**不是印刷页码**。候选同时保留书名、卷次、原PDF路径和定位串，不能跨书套用页码。状态及覆盖记录还列出各卷低文字量的PDF页序，可能是空白、图片或OCR遗漏；每页有记录不代表每页文字已完整提取。没有书签时从卷前目录及正文标题确认篇名。

这是关键词检索，不是语义搜索。统一入口依次检索实际可用的文集，按文集分组返回；不会宣称把所有文集的相关度排成一个通用榜单。最后的摘要列出已搜索和跳过的文集；每套覆盖记录注明实际卷次。代理还需拆词、多轮检索、读上下文，判断证据支持程度。

## 索引与自定义位置

默认数据目录在仓库之外：macOS为 `~/Library/Application Support/<独立Skill名>`，Linux为 `$XDG_DATA_HOME/<独立Skill名>`（未设置时为 `~/.local/share/<独立Skill名>`），Windows为 `%LOCALAPPDATA%\<独立Skill名>`。原PDF仍须保留；源文件移动或修改后，按对应子Skill说明重新配置与重建。

本合集为索引增加了文集身份校验，防止选错数据目录后串用出处。旧独立版索引即使结构相同，也须先用本合集内对应文集的重建脚本重新建立；缺少身份或身份不符时明确拒绝。后续更新索引也使用本合集脚本。原来独立版工具仍可读取新索引的兼容结构，原PDF不变。

仅操作一套时，可给统一入口加`--data-dir`，且必须与该套建索引时的位置一致。多套使用不同自定义位置时，分别设置各自环境变量；完整清单见[文集注册表](references/collections.json)的`data_env`字段。统一入口不会用一个自定义目录混装所有文集。

## 仅安装独立Skill

把 `skills/` 中所需的完整子文件夹复制到自己的Skill目录即可，具体使用见子目录README。只安装独立Skill不附带合集统一入口；无需同时安装其他文集。

## 目录与GitHub上传

```text
SKILL.md                  统一入口指令
README.md                 合集首页与安装说明
requirements.txt
.gitignore
agents/openai.yaml
references/collections.json
scripts/research.py       统一查询与来源定位
skills/                   8套完整的独立Skill
  marx-engels-wenji-research/
  mao-wenji-research/
  deng-xiaoping-wenxuan-research/
  jiang-zemin-wenxuan-research/
  hu-jintao-wenxuan-research/
  xi-governance-research/
  xi-dangjian-wenxuan-research/
  xi-zhuzuo-xuandu-research/
tests/
```

上传到一个仓库时，保留以上层级，让根目录直接出现本README和`SKILL.md`。不能把子目录文件全部摊平在根目录。上传源文件即可，不需要再上传合集ZIP或原书；不要加入本机源清单、索引、OCR全文、页图或个人路径。现有独立仓库可继续保留，合集不自动修改它们。

本合集未添加开源许可证；如要公开授予代码复用权限，先选定许可证。原书材料的权利与工具代码分开处理。

## 验证

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s skills/xi-zhuzuo-xuandu-research/tests -v
```

顶层测试使用合成材料验证统一入口的多套选择、来源定位、实际覆盖和未配置处理；各子Skill保留自身的测试。PDF文字层、OCR和书签都不是校勘本。可用于论文的引文必须核对原页、语境、版本和印刷页码；未核实结果只能标为待核候选。
