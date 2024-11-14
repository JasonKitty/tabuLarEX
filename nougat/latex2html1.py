import re


def remove_grid_lines(latex_table):
    # 去除 \hline, \cline, \toprule, \midrule, \bottomrule
    cleaned_table = re.sub(r'\\cmidrule{\s*}|\\cdashline\{[0-9]+(-[0-9]+)?\}\s*|\\cmidrule\((?:lr|r|l)?\)\{[0-9]+\-[0-9]+\}\s*|\\arrayrulecolor{.*?}\s*|\\caption{.*?}\s*|\\centering\s*|\\hline\s*|\\cline{.*?}\s*|\\toprule\s*|\\midrule\s*|\\bottomrule\s*', '', latex_table)
    
    cleaned_table = re.sub(r'\\tabularnewline', r'\\\\', cleaned_table)
    # # 去除注释
    # cleaned_table = re.sub(r'(?<!\\)%.*$', '', cleaned_table, flags=re.MULTILINE)
    # cleaned_table = re.sub(r'(?<!\\)\[[^\[\]]*\]', '', cleaned_table)
    # 合并连续的空行
    cleaned_table = re.sub(r'\n\s*\n', '\n', cleaned_table)
    
    return cleaned_table.strip(' \n')  # 去除首尾空格

def fix_multi(cell):
    multirow_pattern = r'\\multirow{(\d+)}{.*?}{(.*?)}'
    multicol_pattern = r'\\multicolumn{(\d+)}{.*?}{(.*?)}'
    
    match = re.search(multirow_pattern, cell['content'])
    if match:
        cell['rowspan'] = int(match.group(1))
        cell['content'] = cell['content'].replace(match.group(0), match.group(2).strip(), 1).strip()

    match = re.search(multicol_pattern, cell['content'])
    if match:
        cell['colspan'] = int(match.group(1))
        cell['content'] = cell['content'].replace(match.group(0), match.group(2).strip(), 1).strip()

    return cell    

def grid2html(grid):
    def to_td(grid, r, c):
        if grid[r][c] == '<<' or grid[r][c] == '^^' or grid[r][c] == '..':
            return ''
        td = {'text': grid[r][c], 'rowspan':1, 'colspan': 1}

        for i in range(r + 1, len(grid)):
            if grid[i][c] == '^^':
                td['rowspan'] += 1
            else:
                break
        
        for j in range(c + 1, len(grid[r])):
            if grid[r][j] == '<<':
                td['colspan'] += 1
            else:
                break
        return f'<td rowspan={td["rowspan"]} colspan={td["colspan"]}> {td["text"]} </td>'.replace('rowspan=1', '').replace('colspan=1', '')
        
    
    html = []
    for r in range(len(grid)):
        row = []
        for c in range(len(grid[0])):
            row.append(to_td(grid, r, c))
        html.append(f'<tr> {"".join(row)} </tr>')
    # for row in grid:
    #     html.append('<tr>' + ''.join([to_td(c) for c in row]) + '</tr>')
    
    return '<html><body><table>' + '\n'.join(html) + '</table></body></html>'


def qylatex_to_grid(latex):
    # 提取表格内容
    if not latex.endswith('\\end{tabular}'):
        return 
    pattern = r'\\begin\{tabular\}\s*\{.*?\}(.*?)\\end\{tabular\}'
    matches = re.findall(pattern, latex, re.DOTALL)
    if matches:
        table_content = matches[0]
    else:
        return
    # 提取表格内容

    content = remove_grid_lines(table_content)
    # 获取表格内部的内容
    
    # 将行和列分割
    rows = content.strip(' \n').split(r'\\')

    processed_rows = []

    for row in rows:
        # 去除空行
        if not row.strip():
            continue
        # 处理 multirow 和 multicolumn
        # row = re.sub(r'\\multirow{(\d+)}{.*?}{(.*?)}', lambda m: f"{m.group(2)}" + ("<< " * (int(m.group(1)) - 1)), row)
        # row = re.sub(r'\\multicolumn{(\d+)}{.*?}{(.*?)}', lambda m: f"{m.group(2)}" + ("| " * (int(m.group(1)) - 1)), row)

        # 用 & 分割列
        columns = re.split(r'(?<!\\)&', row)
        columns = [fix_multi({'content': c.strip(' \n'), 'rowspan': 1, 'colspan': 1}) for c in columns]
        # 去除多余的空格并构建行
        processed_rows.append(columns)
    # # 如果最后一行为空, 删除
    # while len(processed_rows) > 0 and len(processed_rows[-1]) == 0:
    #     processed_rows.pop()
    rows = processed_rows
    max_cols = max([sum([it['colspan'] for it in r]) for r in rows])
    # 创建一个空白网格
    grid = [[None for _ in range(max_cols)] for _ in range(len(rows))]
    col_char_num = [[1] for _ in range(max_cols)]
    # 填充网格，处理 rowspan 和 colspan
    r_idx_bias = 0
    for r_idx, row in enumerate(rows):
        r_idx += r_idx_bias
        if r_idx >= len(grid):
            grid.append([None for _ in range(max_cols)])
        c_idx = 0
        current_row_bias = 10000
        for cell in row:
            # 找到第一个未填充的单元格
            if grid[r_idx][c_idx] is not None:
                if cell['content']:
                    while grid[r_idx][c_idx] == '..':
                        c_idx += 1
                else:
                    c_idx += 1
                    continue

            current_row_bias = min(current_row_bias, cell['rowspan'])
            # 填充内容
            grid[r_idx][c_idx] = cell['content']
            col_char_num[c_idx].append(len(cell['content']))
            
            # 处理 rowspan 和 colspan
            for r in range(cell['rowspan']):
                for c in range(cell['colspan']):
                    if r == 0 and c == 0:
                        continue
                    if r == 0:
                        grid[r_idx][c_idx + c] = '<<'
                    elif c == 0:
                        grid[r_idx + r][c_idx] = '^^'
                    else:
                        grid[r_idx + r][c_idx + c] = '..'
            c_idx += cell['colspan']
        r_idx_bias += current_row_bias - 1
    grid = [[c if c is not None else '' for c in r] for r in grid]
    
    return grid


def latex2html(latex_str):
    # 去除注释
    latex_str = re.sub(r'(?<!\\)%.*$', '', latex_str, flags=re.MULTILINE)
    # 去除"\\\\[...]"
    latex_str = re.sub(r'(?<!\\)\\\\\[.*?\]', '', latex_str, flags=re.DOTALL)

    latex_str = latex_str.replace('\n', '').replace('\t', '')
    try:
        grid = qylatex_to_grid(latex_str)
    except IndexError:
        return 
    if not grid:
        return
    html = grid2html(grid)
    return html

