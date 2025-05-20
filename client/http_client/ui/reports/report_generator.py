from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import matplotlib.pyplot as plt
from collections import Counter
import os
import datetime

current_dir = os.path.dirname(__file__)
font_dir = os.path.join(current_dir, "fonts")
pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(font_dir, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(font_dir, "DejaVuSans-Bold.ttf")))

def generate_pdf_report(project, tasks, team_lead, filename, icon_path):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    y = height - 50

    # Заголовок отчёта и логотип
    c.drawImage(icon_path, 50, y - 20, width=40, height=40, mask='auto')
    c.setFont("DejaVu-Bold", 16)
    c.drawString(100, y, "Система управления проектами")
    y -= 50

    # Название отчёта
    c.setFont("DejaVu-Bold", 20)
    c.drawString(50, y, f"Отчёт по проекту: {project['name']}")
    y -= 20
    c.setFont("DejaVu", 12)
    c.drawString(50, y, f"Дата формирования: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}")
    y -= 30

    # Вводная часть
    c.setFont("DejaVu", 12)
    intro = f"Отчёт содержит сводную информацию о текущем состоянии проекта \"{project['name']}\", " \
            f"включая общую статистику задач, текущий статус и аналитику распределения нагрузки между участниками команды."
    for line in split_text(intro, 75):
        c.drawString(50, y, line)
        y -= 15
    y -= 10

    # Основная информация о проекте
    c.setFont("DejaVu-Bold", 14)
    c.drawString(50, y, "Сведения о проекте")
    y -= 20
    c.setFont("DejaVu", 12)
    status_map = {
        "open": "Открыт",
        "in_progress": "В процессе",
        "done": "Выполнен",
        "closed": "Закрыт"
    }

    info_lines = [
        f"Название проекта: {project['name']}",
        f"Описание: {project['description']}",
        f"Руководитель проекта: {team_lead['full_name']}",
        f"Текущий статус: {status_map.get(project['status'], 'Неизвестно')}"
    ]
    for line in info_lines:
        for subline in split_text(line, 100):
            c.drawString(50, y, subline)
            y -= 15
    y -= 10

    # Статистика по задачам
    c.setFont("DejaVu-Bold", 14)
    c.drawString(50, y, "Статистика задач")
    y -= 20
    c.setFont("DejaVu", 12)

    status_counter = Counter(task["status"] for task in tasks)
    priority_avg = round(sum(task["priority"] for task in tasks) / len(tasks), 2) if tasks else 0

    stat_lines = [
        f"Общее количество задач в проекте: {len(tasks)}.",
        f"Средний приоритет задач: {priority_avg}."
    ]
    for status_code, display in status_map.items():
        stat_lines.append(f"{display}: {status_counter.get(status_code, 0)}")

    for line in stat_lines:
        c.drawString(50, y, line)
        y -= 15
    y -= 10

    # Аналитика по исполнителям
    c.setFont("DejaVu-Bold", 14)
    c.drawString(50, y, "Анализ нагрузки по исполнителям")
    y -= 20
    c.setFont("DejaVu", 12)

    assignee_counter = Counter(
        task["assignee"]["full_name"] for task in tasks if task.get("assignee")
    )

    if assignee_counter:
        c.drawString(50, y, "Количество задач, закреплённых за исполнителями:")
        y -= 15
        for assignee, count in assignee_counter.most_common(5):
            c.drawString(70, y, f"{assignee}: {count}")
            y -= 15
    else:
        c.drawString(50, y, "Нет назначенных исполнителей.")
        y -= 15
    y -= 10

    # Диаграмма распределения задач
    c.setFont("DejaVu-Bold", 14)
    c.drawString(50, y, "График распределения задач по статусам")
    y -= 260

    labels = [status_map.get(k, k) for k in status_counter.keys()]
    sizes = [v for v in status_counter.values()]
    colors_list = ['#6BA292', '#FFC107', '#4CAF50', '#F44336']

    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors_list)
    ax.axis('equal')
    chart_path = os.path.join("/tmp", "status_chart.png")
    plt.savefig(chart_path)
    plt.close()

    c.drawImage(chart_path, 100, y, width=400, height=250)
    c.save()
    os.remove(chart_path)

def split_text(text, max_length):
    """
    Вспомогательная функция для переноса длинных строк по max_length символов.
    """
    words = text.split()
    lines = []
    current = ""

    for word in words:
        if len(current + word) < max_length:
            current += word + " "
        else:
            lines.append(current.strip())
            current = word + " "
    if current:
        lines.append(current.strip())
    return lines


