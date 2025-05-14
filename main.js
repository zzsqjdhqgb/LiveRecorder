const axios = require('axios');
const fs = require('fs');
const ffmpeg = require('fluent-ffmpeg');

const url = 'https://example.com/video.flv'; // 远程 FLV 视频 URL
const outputFile = 'output.flv'; // 保存的本地文件名

// 创建一个读取流并连接到 ffmpeg
const writeStream = fs.createWriteStream(outputFile);

axios({
    method: 'get',
    url: url,
    responseType: 'stream',  // 确保响应是流的形式
})
.then(response => {
    const videoStream = response.data;

    // 使用 ffmpeg 处理视频流并实时写入文件
    ffmpeg(videoStream)
        .output(writeStream)
        .on('end', () => {
            console.log('录制完成');
        })
        .on('error', (err) => {
            console.error('录制出错: ', err);
        })
        .run();
})
.catch(err => {
    console.error('无法获取视频流: ', err);
});
