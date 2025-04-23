from flask import Flask, render_template, request, send_from_directory, jsonify
import os
import torch
from PIL import Image
import uuid
import traceback
import logging
import sys
import io
import re
from briarmbg import BriaRMBG
from utilities import preprocess_image, postprocess_image
import numpy as np
from werkzeug.utils import secure_filename

# 设置环境变量，禁用所有可能的彩色输出
os.environ['WERKZEUG_CONSOLE_COLOR'] = '0'
os.environ['WERKZEUG_RUN_WITHOUT_RELOADER'] = 'true'
os.environ['WERKZEUG_DISABLE_RELOADER'] = 'true'
os.environ['WERKZEUG_DEBUG_PIN'] = 'off'
os.environ['ANSI_COLORS_DISABLED'] = '1'
os.environ['NO_COLOR'] = '1'
os.environ['FORCE_COLOR'] = '0'

# 设置控制台输出编码为UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# 创建一个过滤器，移除ANSI转义序列
class AnsiFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    
    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = self.ansi_escape.sub('', record.msg)
        return True

# 自定义日志处理器，确保使用UTF-8编码并移除ANSI转义序列
class UTF8StreamHandler(logging.StreamHandler):
    def __init__(self, stream=None):
        super().__init__(stream)
        self.stream = io.TextIOWrapper(
            self.stream.buffer, encoding='utf-8', errors='replace')
        self.addFilter(AnsiFilter())

# 设置日志记录
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)
    # 替换默认的StreamHandler
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler):
            logging.getLogger().removeHandler(handler)
    
    # 添加自定义处理器
    handler = UTF8StreamHandler()
    logging.getLogger().addHandler(handler)

# 为werkzeug日志也添加过滤器
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addFilter(AnsiFilter())

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

# 设置日志记录
# 防止重复配置日志
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 确保目录使用绝对路径
app.config['UPLOAD_FOLDER'] = os.path.abspath(app.config['UPLOAD_FOLDER'])

app.logger.info(f"上传目录: {app.config['UPLOAD_FOLDER']}")

# 加载模型
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
app.logger.info(f"使用设备: {device}")
model = None

# 预加载模型
def load_model():
    global model
    if model is None:
        app.logger.info("正在加载模型...")
        model = BriaRMBG.from_pretrained("briaai/RMBG-1.4")
        model.to(device)
        model.eval()
        app.logger.info("模型加载完成")
    return model

# 防止在调试模式下重复加载模型
# 使用全局变量跟踪是否已经初始化
app_initialized = False

def initialize_app():
    global app_initialized
    if not app_initialized:
        # 仅在主进程中加载模型
        if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
            app.logger.info("预加载模型...")
            load_model()
            app.logger.info("应用初始化完成")
            app_initialized = True

# 在第一次请求时预加载模型
with app.app_context():
    initialize_app()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        app.logger.error('没有文件部分')
        return jsonify({'error': '没有文件部分'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        app.logger.error('没有选择文件')
        return jsonify({'error': '没有选择文件'}), 400
    
    if file and allowed_file(file.filename):
        try:
            # 生成唯一文件名
            filename = str(uuid.uuid4()) + '.' + file.filename.rsplit('.', 1)[1].lower()
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            app.logger.info(f'文件已保存到: {filepath}')
            
            # 加载模型
            net = load_model()
            app.logger.info('模型已加载')
            
            # 处理图像
            orig_im = np.array(Image.open(filepath))
            orig_im_size = orig_im.shape[0:2]
            
            # 调整输入尺寸以提高性能
            # 对于较大的图像，使用较小的输入尺寸以加快处理
            max_dim = max(orig_im_size)
            if max_dim > 1500:
                model_input_size = [1024, 1024]  # 大图像使用较小尺寸
            elif max_dim > 800:
                model_input_size = [768, 768]    # 中等图像
            else:
                model_input_size = [512, 512]    # 小图像
                
            app.logger.info(f'原始图像尺寸: {orig_im_size}, 处理尺寸: {model_input_size}')
            
            # 预处理
            image = preprocess_image(orig_im, model_input_size).to(device)
            app.logger.info('图像预处理完成')
            
            # 推理
            result = net(image)
            app.logger.info('模型推理完成')
            
            # 后处理
            result_image = postprocess_image(result[0][0], orig_im_size)
            app.logger.info('图像后处理完成')
            
            # 创建透明背景图像
            pil_im = Image.fromarray(result_image)
            no_bg_image = Image.new("RGBA", pil_im.size, (0, 0, 0, 0))
            orig_image = Image.open(filepath)
            no_bg_image.paste(orig_image, mask=pil_im)
            
            # 生成唯一的文件名（仅用于前端显示）
            result_filename = filename.rsplit('.', 1)[0] + '.png'
            
            # 将图像转换为Base64字符串
            import io
            import base64
            buffer = io.BytesIO()
            no_bg_image.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            app.logger.info('图像已处理并转换为Base64格式')
            
            return jsonify({
                'success': True,
                'original': filename,
                'result': result_filename,
                'image_data': img_str
            })
            
        except Exception as e:
            app.logger.error(f'处理过程中出错: {str(e)}')
            app.logger.error(traceback.format_exc())
            return jsonify({'error': str(e)}), 500
    
    app.logger.error(f'不允许的文件类型: {file.filename}')
    return jsonify({'error': '不允许的文件类型'}), 400

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    app.logger.info(f'请求上传文件: {filename}')
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# 移除了结果文件路由，因为现在使用Base64直接传输图像数据

if __name__ == '__main__':
    # 设置日志级别，显示访问日志
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.INFO)  # 使用INFO级别显示访问日志
    
    # 禁用Werkzeug的彩色输出
    import os
    os.environ['WERKZEUG_RUN_WITHOUT_RELOADER'] = 'true'
    os.environ['WERKZEUG_DISABLE_RELOADER'] = 'true'
    os.environ['WERKZEUG_DEBUG_PIN'] = 'off'
    os.environ['WERKZEUG_CONSOLE_COLOR'] = '0'  # 禁用控制台颜色
    
    # 获取本机内网IP地址
    import socket
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "127.0.0.1"
    
    # 显示服务器URL信息
    print("\n\n服务器已启动，请访问：")
    print("- 本机访问：http://127.0.0.1:5000")
    print(f"- 其他设备访问：http://{local_ip}:5000\n")
    
    # 启动应用，允许外部访问
    app.run(debug=False, threaded=False, use_reloader=False, host='0.0.0.0', port=5000)
