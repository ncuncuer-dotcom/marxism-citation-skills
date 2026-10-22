#!/usr/bin/env python3
"""Dispatch to bundled local collections without combining corpora or citations."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLLECTIONS = json.loads((ROOT / 'references' / 'collections.json').read_text(encoding='utf-8'))
BY_ID = {item['id']: item for item in COLLECTIONS}


def emit(value):
    print(json.dumps(value, ensure_ascii=False))


def backend(item, args, data_dir=None):
    script = ROOT / 'skills' / item['skill'] / 'scripts' / 'retrieve.py'
    if not script.is_file():
        raise ValueError('合集缺少{}检索脚本，请完整安装或解压合集。'.format(item['title']))
    command = [sys.executable, str(script), *args]
    if data_dir:
        command += ['--data-dir', str(Path(data_dir).expanduser().resolve())]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        raise ValueError('检索超过60秒，请缩小范围或检查源文件。')
    if result.returncode:
        raise ValueError(result.stderr.strip() or '子集检索失败。')
    try:
        return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    except json.JSONDecodeError:
        raise ValueError('子集返回了无效JSON。')


def status(item, data_dir=None):
    try:
        rows = backend(item, ['--status'], data_dir)
        if len(rows) != 1 or not isinstance(rows[0], dict):
            raise ValueError('子集状态格式无效。')
        raw = rows[0]
        volumes = raw.get('volumes', [])
        present = [v['volume'] for v in volumes]
        return {'type': 'status', 'collection_id': item['id'], 'collection_title': item['title'],
                'ready': bool(raw.get('ready')), 'indexed_volumes': present,
                'missing_volumes': sorted(set(range(1, item['volumes'] + 1)) - set(present)),
                'indexed_pages': raw.get('indexed_pages', 0), 'data_dir': raw.get('data_dir'),
                'source_errors': raw.get('source_errors', []),
                'low_text_pages_by_volume': {str(v['volume']): v.get('low_text_pdf_pages', []) for v in volumes},
                'text_coverage_note': '每页索引记录不代表每页都有可检索文字；低文字量页可能为空白、图像或OCR遗漏，须查原页。',
                'note': raw.get('note') or raw.get('next_step', '')}
    except (OSError, ValueError) as exc:
        return {'type': 'status', 'collection_id': item['id'], 'collection_title': item['title'],
                'ready': False, 'indexed_volumes': [], 'missing_volumes': list(range(1, item['volumes'] + 1)),
                'indexed_pages': 0, 'error': str(exc)}


def tagged(item, row):
    result = dict(row)
    result.update(collection_id=item['id'], collection_title=item['title'])
    if 'candidate_excerpt' in row:
        result['match_quality'] = 'exact_terms' if row.get('matched_terms') else 'tokens_only'
    if 'volume' in row and 'pdf_page' in row:
        result['local_reference'] = '{}:{}:{}'.format(item['id'], row['volume'], row['pdf_page'])
    return result


def main():
    parser = argparse.ArgumentParser(description='8套马理论文献本地检索统一入口；关键词命中不等于引文已核实。')
    parser.add_argument('terms', nargs='*', help='短关键词或短语；请由代理先拆解论文主题')
    parser.add_argument('--collection', action='append', choices=list(BY_ID), help='选定文集，可重复；默认检查或检索全部8套')
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--status', action='store_true', help='查看各文集实际已索引范围和可用状态')
    actions.add_argument('--page', help='文集ID:卷:PDF页序，例如 mao:7:30')
    actions.add_argument('--catalogue', action='store_true', help='查看所选一套的PDF书签导航')
    parser.add_argument('--limit', type=int, default=3, help='每套最多返回几条候选，1—50；不同文集不比较分值')
    parser.add_argument('--context', type=int, default=0, help='--page前后各读0—5页')
    parser.add_argument('--render', help='与--page合用，渲染对应原PDF页为PNG')
    parser.add_argument('--data-dir', help='仅选择一套时使用：覆盖该套默认数据目录')
    args = parser.parse_args()
    if not 1 <= args.limit <= 50 or not 0 <= args.context <= 5:
        parser.error('--limit必须为1—50，--context必须为0—5。')
    if args.terms and (args.status or args.page or args.catalogue):
        parser.error('关键词检索不能与状态、页面或书签命令合用。')
    if not args.terms and not (args.status or args.page or args.catalogue):
        parser.error('请给出关键词或--status、--page、--catalogue。')
    if (args.render or args.context) and not args.page:
        parser.error('--render和--context必须与--page合用。')
    selected = list(dict.fromkeys(args.collection or list(BY_ID)))
    page = None
    if args.page:
        parts = args.page.split(':')
        if len(parts) != 3 or parts[0] not in BY_ID:
            parser.error('--page应为文集ID:卷:PDF页序，例如 mao:7:30。')
        selected = [parts[0]]
        if args.collection and list(dict.fromkeys(args.collection)) != selected:
            parser.error('--collection与--page中的文集不一致。')
        page = ':'.join(parts[1:])
    if args.catalogue and len(selected) != 1:
        parser.error('--catalogue请用--collection指定一套文集。')
    if args.data_dir and len(selected) != 1:
        parser.error('--data-dir仅适用于一套文集；多套自定义位置请分别设置其环境变量。')
    if args.status:
        for key in selected:
            emit(status(BY_ID[key], args.data_dir))
        return
    if args.page or args.catalogue:
        item = BY_ID[selected[0]]
        command = ['--page', page, '--context', str(args.context)] if page else ['--catalogue']
        if args.render:
            command += ['--render', args.render]
        try:
            for row in backend(item, command, args.data_dir):
                emit(tagged(item, row))
        except (OSError, ValueError) as exc:
            parser.exit(1, '读取失败：{}\n'.format(exc))
        return
    searched, skipped, count = [], [], 0
    for key in selected:
        item = BY_ID[key]
        current = status(item, args.data_dir)
        if not current['ready']:
            skipped.append(key)
            emit(dict(current, searched=False))
            continue
        try:
            rows = backend(item, [*args.terms, '--limit', str(args.limit)], args.data_dir)
            for row in rows:
                emit(tagged(item, row))
                count += int('candidate_excerpt' in row)
            searched.append(key)
            emit({'type': 'coverage', 'collection_id': key, 'collection_title': item['title'],
                  'indexed_volumes': current['indexed_volumes'], 'missing_volumes': current['missing_volumes'],
                  'low_text_pages_by_volume': current.get('low_text_pages_by_volume', {}),
                  'text_coverage_note': current.get('text_coverage_note', '')})
        except (OSError, ValueError) as exc:
            skipped.append(key)
            emit({'type': 'error', 'collection_id': key, 'collection_title': item['title'], 'error': str(exc)})
    emit({'type': 'summary', 'searched': searched, 'skipped': skipped, 'candidates': count,
          'note': '仅检索已列出的实际卷次；缺失文集或卷次不属于检索范围。结果按文集分组，未作跨文集相关性排名；所有引文须回读原页。'})
    if not searched:
        parser.exit(1, '没有可用索引，请按README为自己的PDF建立索引。\n')


if __name__ == '__main__':
    main()
