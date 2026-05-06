"""
Quality Check - Web app para auditoria de qualidade de respostas de pesquisa.
Sobe arquivo .xlsx do QuestionPro/SurveyMonkey e identifica respostas suspeitas.
"""
import io
import json
import os
import secrets
from pathlib import Path

import pandas as pd
from flask import (
    Flask, request, render_template, send_file, jsonify, redirect, url_for
)
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment

from quality import analyze

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

WORK_DIR = Path("/tmp/qc_work")
WORK_DIR.mkdir(exist_ok=True)


def make_output_xlsx(original_path, results_df, output_path):
    """
    Gera o xlsx final: arquivo original + colunas de flag + aba 'Auditoría'.
    """
    # Carrega o original com pandas pra preservar todas as colunas
    df_original = pd.read_excel(original_path, sheet_name=0)

    # Junta as colunas de flag pelo ID
    flag_cols = [
        'classificacao', 'score_suspeita',
        'flag_ip_duplicado', 'flag_tempo_curto', 'flag_marca_oleo',
        'flag_gibberish', 'flag_lugar_nao_marca', 'flag_so_simbolos',
        'flag_muitas_marcas_raras', 'flag_copy_paste',
        'motivos',
    ]
    merge = results_df[['ID de respuesta'] + flag_cols].copy()

    # Converte ID pra mesmo tipo (float em ambos)
    df_original['ID de respuesta'] = pd.to_numeric(
        df_original['ID de respuesta'], errors='coerce'
    )
    merge['ID de respuesta'] = pd.to_numeric(
        merge['ID de respuesta'], errors='coerce'
    )

    df_full = df_original.merge(merge, on='ID de respuesta', how='left')

    # Aba resumo
    summary_rows = []
    summary_rows.append(['Total de respondentes', len(results_df)])
    summary_rows.append(['', ''])
    for cls, n in results_df['classificacao'].value_counts().items():
        summary_rows.append([cls, n])
    summary_rows.append(['', ''])
    summary_rows.append(['Detalhes por flag:', ''])
    for col in flag_cols:
        if col.startswith('flag_'):
            n = int(results_df[col].sum())
            summary_rows.append([col, n])

    df_summary = pd.DataFrame(summary_rows, columns=['Métrica', 'Valor'])

    # Aba só com suspeitos (revisão prioritária)
    df_suspects = results_df[results_df['score_suspeita'] >= 20].sort_values(
        'score_suspeita', ascending=False
    )

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_summary.to_excel(writer, sheet_name='Resumen', index=False)
        df_suspects.to_excel(writer, sheet_name='Revisar', index=False)
        df_full.to_excel(writer, sheet_name='Datos completos', index=False)

    # Formatação - destacar a linha por classificação
    wb = load_workbook(output_path)
    ws = wb['Datos completos']

    # Procura a coluna 'classificacao'
    header = [c.value for c in ws[1]]
    if 'classificacao' in header:
        cls_col = header.index('classificacao') + 1
        red_fill = PatternFill('solid', start_color='FFCDD2')
        yellow_fill = PatternFill('solid', start_color='FFF9C4')
        for row in range(2, ws.max_row + 1):
            val = ws.cell(row=row, column=cls_col).value
            if val and 'Alta suspeita' in str(val):
                for col in range(1, ws.max_column + 1):
                    ws.cell(row=row, column=col).fill = red_fill
            elif val and 'Revisar' in str(val):
                for col in range(1, ws.max_column + 1):
                    ws.cell(row=row, column=col).fill = yellow_fill

    # Formata o resumo
    ws_sum = wb['Resumen']
    ws_sum['A1'].font = Font(bold=True, size=12)
    ws_sum['B1'].font = Font(bold=True, size=12)
    ws_sum.column_dimensions['A'].width = 35
    ws_sum.column_dimensions['B'].width = 15

    wb.save(output_path)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400

    f = request.files['file']
    if not f.filename:
        return jsonify({'error': 'Arquivo vazio'}), 400

    if not f.filename.lower().endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'Por favor envie um arquivo .xlsx'}), 400

    try:
        time_threshold = int(request.form.get('time_threshold', 8))
    except ValueError:
        time_threshold = 8

    # Salva temporário
    job_id = secrets.token_hex(8)
    input_path = WORK_DIR / f"{job_id}_input.xlsx"
    output_path = WORK_DIR / f"{job_id}_output.xlsx"
    f.save(input_path)

    try:
        df = pd.read_excel(input_path, sheet_name=0)
        results, meta = analyze(df, time_threshold_min=time_threshold)
        make_output_xlsx(input_path, results, output_path)

        # Resumo pra mostrar no dashboard
        summary = {
            'job_id': job_id,
            'total': len(results),
            'classificacoes': results['classificacao'].value_counts().to_dict(),
            'flags': {
                col: int(results[col].sum())
                for col in results.columns if col.startswith('flag_')
            },
            'whitelist_size': len(meta['whitelist']),
            'whitelist_sample': sorted(meta['whitelist'])[:30],
            'tempo_minimo_min': time_threshold,
            'top_suspeitos': results.nlargest(20, 'score_suspeita')[
                ['ID de respuesta', 'Dirección IP', 'Tiempo (min)',
                 'classificacao', 'score_suspeita', 'motivos']
            ].fillna('').to_dict('records'),
        }

        return jsonify(summary)

    except Exception as e:
        return jsonify({'error': f'Erro ao processar: {type(e).__name__}: {e}'}), 500


@app.route('/download/<job_id>')
def download(job_id):
    # Validação: job_id deve ser hex puro
    if not all(c in '0123456789abcdef' for c in job_id) or len(job_id) != 16:
        return "Invalid job ID", 400

    output_path = WORK_DIR / f"{job_id}_output.xlsx"
    if not output_path.exists():
        return "Arquivo expirado ou não encontrado", 404

    return send_file(
        output_path,
        as_attachment=True,
        download_name='auditoria_calidad.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=port)
