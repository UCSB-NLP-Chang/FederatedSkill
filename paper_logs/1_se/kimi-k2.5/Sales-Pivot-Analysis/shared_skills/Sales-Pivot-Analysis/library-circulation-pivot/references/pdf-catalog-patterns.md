# PDF Catalog Parsing Patterns

## Common Library System Export Formats

### Format A: Fixed-Width Columns
```
7001  The Great Gatsby              Fiction      1925
7002  To Kill a Mockingbird         Fiction      1960
7003  Sapiens: A Brief History      Non-Fiction  2011
```

```python
lines = [l for l in pdf_text.split('\n') if l.strip()]
data = []
for line in lines:
    if len(line) >= 40:  # minimum width
        book_id = line[0:4].strip()
        title = line[5:35].strip()
        genre = line[35:50].strip()
        year = line[50:55].strip()
        data.append([book_id, title, genre, year])
```

### Format B: Labeled Rows (Multi-line per record)
```
Book ID: 7001
Title: The Great Gatsby
Author: F. Scott Fitzgerald
Genre: Fiction
Year: 1925
```

```python
import re
records = re.split(r'Book ID:\s*', pdf_text)[1:]  # split on delimiter
data = []
for record in records:
    book_id = re.search(r'^(\d+)', record).group(1)
    title = re.search(r'Title:\s*(.+?)(?:\n|Author:)', record, re.DOTALL)
    genre = re.search(r'Genre:\s*(\S+)', record)
    year = re.search(r'Year:\s*(\d{4})', record)
    data.append([book_id, title.group(1).strip() if title else None,
                 genre.group(1) if genre else None, year.group(1) if year else None])
```

### Format C: Pipe or Comma Delimited
```
7001|The Great Gatsby|Fitzgerald|Fiction|1925
7002|To Kill a Mockingbird|Lee|Fiction|1960
```

```python
# Simple split after extracting text block
data = []
for line in pdf_text.split('\n'):
    if '|' in line:
        parts = line.split('|')
        if len(parts) >= 5:
            data.append([p.strip() for p in parts[:5]])
```

## Genre Normalization

```python
genre_map = {
    'sci-fi': 'Science Fiction',
    'scifi': 'Science Fiction',
    'non-fiction': 'Non-Fiction',
    'nonfiction': 'Non-Fiction',
    'bio': 'Biography',
    'hist': 'History'
}
df['GENRE'] = df['GENRE'].str.strip().str.title()
df['GENRE'] = df['GENRE'].replace(genre_map)
```

## Year Extraction from Variants

```python
def extract_year(val):
    if pd.isna(val):
        return None
    val = str(val)
    # Direct year
    if val.isdigit() and len(val) == 4:
        return int(val)
    # From parentheses: (2011) or c2011
    m = re.search(r'[c\(]?(\d{4})[\)]?', val)
    if m:
        return int(m.group(1))
    return None

df['YEAR_PUBLISHED'] = df['YEAR_PUBLISHED'].apply(extract_year)
```
