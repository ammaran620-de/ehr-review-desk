"""Pagination of review cases, independent of model scoring and evaluation."""
PAGE_SIZE = 20


def page_count(rows):
    return max(1, (len(rows) + PAGE_SIZE - 1) // PAGE_SIZE)


def alert_page(rows, page_number):
    page_number = min(max(int(page_number), 1), page_count(rows))
    start = (page_number - 1) * PAGE_SIZE
    return rows[start:start + PAGE_SIZE]
