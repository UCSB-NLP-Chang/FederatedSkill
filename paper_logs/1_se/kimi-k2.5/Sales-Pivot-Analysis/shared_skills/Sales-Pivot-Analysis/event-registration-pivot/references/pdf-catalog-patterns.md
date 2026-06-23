# PDF Event Catalog Parsing Patterns

## Common Event Management System Export Formats

### Format A: Fixed-Width Columns
```
8001  Intro to ML Workshop              AI/ML                Room A           50
8002  Cloud Security Summit             Security             Main Hall       200
8003  Data Analytics Deep Dive          Data Science         Room B          150
```

```python
lines = [l for l in pdf_text.split('\n') if l.strip() and l[0:4].isdigit()]
data = []
for line in lines:
    event_id = line[0:4].strip()
    name = line[5:35].strip()
    track = line[36:55].strip()
    venue = line[56:72].strip()
    capacity = line[73:].strip()
    data.append([event_id, name, track, venue, capacity])
```

### Format B: Labeled Fields
```
Event: 8001 - Intro to ML Workshop
Track: AI/ML
Venue: Room A
Capacity: 50
```

```python
import re
records = re.split(r'Event:\s*', pdf_text)[1:]
data = []
for rec in records:
    event_id = re.search(r'^(\d+)', rec).group(1)
    name = re.search(r'-\s*(.+?)(?:\n|Track:)', rec, re.DOTALL)
    track = re.search(r'Track:\s*([\w\s/]+)', rec)
    venue = re.search(r'Venue:\s*([\w\s]+)', rec)
    capacity = re.search(r'Capacity:\s*(\d+)', rec)
    data.append([event_id, 
                 name.group(1).strip() if name else None,
                 track.group(1).strip() if track else None,
                 venue.group(1).strip() if venue else None,
                 capacity.group(1) if capacity else None])
```

### Format C: Pipe Delimited
```
8001|Intro to ML Workshop|AI/ML|Room A|50
8002|Cloud Security Summit|Security|Main Hall|200
```

```python
data = []
for line in pdf_text.split('\n'):
    if '|' in line:
        parts = line.split('|')
        if len(parts) >= 5:
            data.append([p.strip() for p in parts[:5]])
```

## Track Name Normalization

```python
track_map = {
    'ai ml': 'AI/ML',
    'aiml': 'AI/ML',
    'cloud': 'Cloud Infrastructure',
    'data': 'Data Science',
    'web': 'Web Development',
    'sec': 'Security'
}

df['TRACK'] = df['TRACK'].str.strip().str.lower()
df['TRACK'] = df['TRACK'].replace(track_map)
# Final pass for any non-matches
df['TRACK'] = df['TRACK'].str.title()
```

## Venue Name Normalization

```python
venue_map = {
    'mainhall': 'Main Hall',
    'room-a': 'Room A',
    'room b': 'Room B',
    'auditorium': 'Auditorium',
    'workshop': 'Workshop Lab'
}
df['VENUE'] = df['VENUE'].str.strip().str.title()
df['VENUE'] = df['VENUE'].replace(venue_map)
```
