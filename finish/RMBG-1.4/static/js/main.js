document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-btn');
    const loading = document.getElementById('loading');
    const resultContainer = document.getElementById('result-container');
    const originalPreview = document.getElementById('original-preview');
    const resultPreview = document.getElementById('result-preview');
    const downloadBtn = document.getElementById('download-btn');
    const helpBtn = document.getElementById('help-btn');
    const instructionsCard = document.getElementById('instructions');
    
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const file = fileInput.files[0];
        if (!file) {
            alert('请选择一个图片文件');
            return;
        }
        
        // 显示加载状态
        loading.classList.remove('d-none');
        resultContainer.innerHTML = '';
        uploadBtn.disabled = true;
        
        // 创建FormData对象
        const formData = new FormData();
        formData.append('file', file);
        
        // 显示原始图片预览
        const reader = new FileReader();
        reader.onload = function(e) {
            originalPreview.innerHTML = `<img src="${e.target.result}" alt="原始图片">`;
        };
        reader.readAsDataURL(file);
        
        // 发送请求
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            loading.classList.add('d-none');
            uploadBtn.disabled = false;
            
            if (data.success) {
                // 使用Base64数据显示结果图片
                const resultImg = document.createElement('img');
                resultImg.src = `data:image/png;base64,${data.image_data}`;
                resultImg.alt = '处理后图片';
                resultContainer.innerHTML = '';
                resultContainer.appendChild(resultImg);
                
                // 显示结果预览
                resultPreview.innerHTML = `<img src="data:image/png;base64,${data.image_data}" alt="处理后图片">`;
                
                // 设置下载按钮
                downloadBtn.href = `data:image/png;base64,${data.image_data}`;
                downloadBtn.download = `背景移除_${data.result}`;
                downloadBtn.classList.remove('d-none');
            } else {
                resultContainer.innerHTML = `<div class="alert alert-danger">${data.error || '处理失败'}</div>`;
            }
        })
        .catch(error => {
            loading.classList.add('d-none');
            uploadBtn.disabled = false;
            resultContainer.innerHTML = `<div class="alert alert-danger">发生错误: ${error.message}</div>`;
        });
    });
    
    // 文件选择变化时预览
    fileInput.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                originalPreview.innerHTML = `<img src="${e.target.result}" alt="原始图片">`;
                resultPreview.innerHTML = `<p class="text-muted">等待处理...</p>`;
            };
            reader.readAsDataURL(file);
            
            // 重置结果区域
            resultContainer.innerHTML = `<p class="text-muted">点击"上传并处理"按钮开始处理</p>`;
            downloadBtn.classList.add('d-none');
        }
    });
    
    // 帮助按钮点击事件
    helpBtn.addEventListener('click', function(e) {
        e.preventDefault();
        
        // 滚动到页面顶部
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        // 等待滚动完成后执行高亮
        setTimeout(function() {
            // 第一次高亮 - 快速添加
            instructionsCard.classList.add('blink-card');
            
            // 等待高亮显示一下
            setTimeout(function() {
                // 移除第一次高亮
                instructionsCard.classList.remove('blink-card');
                
                // 短暂停后再次高亮
                setTimeout(function() {
                    // 第二次高亮
                    instructionsCard.classList.add('blink-card');
                    
                    // 短暂停后移除高亮
                    setTimeout(function() {
                        // 移除第二次高亮
                        instructionsCard.classList.remove('blink-card');
                    }, 300);
                }, 200);
            }, 300);
        }, 400);
    });
});
