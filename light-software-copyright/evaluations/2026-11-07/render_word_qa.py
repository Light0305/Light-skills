"""Native Word rendering of explicitly listed, isolated evaluation documents."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--spec",required=True)
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    spec=json.loads(Path(args.spec).read_text(encoding="utf-8"))
    paths=[Path(p) for p in spec.get("paths",spec.get("docx",[]))]
    if not paths: raise ValueError("No explicit evaluation DOCX inputs")
    out=Path(args.out).resolve()
    out.mkdir(parents=True,exist_ok=False)
    import pythoncom
    import win32com.client
    import fitz
    from PIL import Image,ImageDraw
    pythoncom.CoInitialize()
    app=None; results=[]
    try:
        app=win32com.client.DispatchEx("Word.Application")
        app.Visible=False; app.DisplayAlerts=0; app.AutomationSecurity=3
        for i,path in enumerate(paths,1):
            before=sha(path)
            folder=out/str(i); folder.mkdir()
            pdf=folder/"word.pdf"
            doc=app.Documents.Open(str(path),ConfirmConversions=False,ReadOnly=True,
                                   AddToRecentFiles=False,Visible=False)
            try:
                doc.Repaginate()
                pages=doc.ComputeStatistics(2)
                doc.ExportAsFixedFormat(str(pdf),17,OpenAfterExport=False)
            finally:
                doc.Close(False)
            assert sha(path)==before, "Read-only rendering modified input"
            images=[]; texts=[]
            with fitz.open(pdf) as rendered:
                assert len(rendered)==pages
                for j,page in enumerate(rendered,1):
                    dest=folder/f"page-{j}.png"
                    page.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False).save(dest)
                    images.append(str(dest))
                    texts.append(page.get_text())
            (folder/"page-text.json").write_text(json.dumps(texts,ensure_ascii=False,indent=2),encoding="utf-8")
            thumbs=[]
            for j,img in enumerate(images,1):
                im=Image.open(img).convert("RGB")
                draw=ImageDraw.Draw(im); draw.text((15,10),f"Page {j}",fill="black")
                thumbs.append(im)
            width=max(t.width for t in thumbs); height=max(t.height for t in thumbs)
            cols=min(len(thumbs),3); rows=(len(thumbs)+cols-1)//cols
            sheet=Image.new("RGB",(width*cols,height*rows),(215,215,215))
            for j,im in enumerate(thumbs): sheet.paste(im,((j%cols)*width,(j//cols)*height))
            sheetpath=folder/"all-pages.png"; sheet.save(sheetpath)
            results.append({"docx":str(path),"sha256":before,"pdf":str(pdf),"pdf_sha256":sha(pdf),
                            "pages":pages,"images":images,"contact_sheet":str(sheetpath),
                            "input_unchanged":True})
    finally:
        if app: app.Quit()
        pythoncom.CoUninitialize()
    (out/"render-result.json").write_text(json.dumps({"engine":"Microsoft Word COM",
        "read_only":True,"documents":results},ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"out":str(out),"documents":[{"name":Path(r["docx"]).name,"pages":r["pages"],
        "preview":r["contact_sheet"]} for r in results]},ensure_ascii=False))


if __name__=="__main__":
    main()
