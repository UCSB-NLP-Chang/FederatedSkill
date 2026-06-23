# Adding Slides to a PPTX

Adding a new slide requires 5 coordinated changes. Missing any step corrupts the file or causes the slide to be ignored.

## Prerequisite: Check Existing rIds

**CRITICAL**: Relationship IDs (rId1, rId2, etc.) must be unique. Before adding, check:
```bash
cat pptx_extracted/ppt/_rels/presentation.xml.rels
```

Common mappings (varies by file):
- rId1: slideMaster
- rId2-rId7: slides (typically)
- rId8+: presProps, viewProps, theme, tableStyles

Never assume rId8 is free. Always verify.

## 5-Step Workflow

### 1. Create the slide XML
Copy an existing slide as template:
```bash
cp ppt/slides/slide1.xml ppt/slides/slide4.xml
```
Edit the new file with your content.

### 2. Create slide relationships
Create `ppt/slides/_rels/slide4.xml.rels`:
```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>
```

### 3. Add to presentation.xml
Add a new `<p:sldId>` entry:
```xml
<p:sldId id="260" r:id="rId12"/>
```
- Use next available numeric id (256+)
- Use an unused rId (verified in step 0)

### 4. Add relationship mapping
Add to `ppt/_rels/presentation.xml.rels`:
```xml
<Relationship Id="rId12" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide4.xml"/>
```

### 5. Register content type (CRITICAL)
Add to `[Content_Types].xml` inside `<Types>`:
```xml
<Override PartName="/ppt/slides/slide4.xml" 
          ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
```

**Common error**: Forgetting the leading `/` in PartName. It must be `/ppt/slides/slide4.xml`, not `ppt/slides/slide4.xml`.

## Verification

After repacking, verify:
1. File opens without errors
2. Slide count matches expected
3. New slide appears in correct position
4. No duplicate rIds in presentation.xml.rels
5. **Content type registered**: Check `[Content_Types].xml` contains the new slide

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| File won't open | Duplicate rId | Check all rIds are unique |
| Missing slide | No sldId entry | Add to presentation.xml |
| Missing slide | No content type | Add Override to `[Content_Types].xml` |
| Empty slide | No relationship file | Create slideN.xml.rels |
| Wrong position | Wrong sldId order | Reorder sldId elements |
| "Repair" dialog | Wrong PartName path | Ensure leading `/` in PartName attribute |
