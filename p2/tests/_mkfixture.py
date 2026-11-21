
import docx, sys
sys.stdout.reconfigure(encoding="utf-8")
d = docx.Document()
d.add_heading("自测夹具（虚构数据，仅验证管道）", 1)
d.add_paragraph("产品册节选。鼓式刹车片 GY-D-0001，鼓径 420mm，片宽 200mm，厚度 18mm，材质半金属，摩擦系数 0.38。适配车桥 BPW ECO Plus。")
d.add_paragraph("磨损率 0.12mm/1000km，依据测试报告 TR-2023-0451 第 7 页。参考价 180-240 元，MOQ 200。")
t = d.add_table(rows=2, cols=4)
for i, v in enumerate(["型号", "鼓径", "片宽", "材质"]):
    t.cell(0, i).text = v
for i, v in enumerate(["GY-D-0002", "410", "180", "陶瓷"]):
    t.cell(1, i).text = v
d.save(sys.argv[1])
