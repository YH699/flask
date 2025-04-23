from briarmbg import BriaRMBG
from MyPipe import RMBGPipe
from PIL import Image

if __name__ == "__main__":
    # 创建模型
    model = BriaRMBG.from_pretrained("briaai/RMBG-1.4")
    
    # 创建pipeline
    pipe = RMBGPipe(model=model)
    
    # 处理图像
    result = pipe("shuru.jpg")
    
    # 保存结果
    result.save("shuchu_pipe.png")
    print("背景移除完成，结果已保存为 shuchu_pipe.png")
