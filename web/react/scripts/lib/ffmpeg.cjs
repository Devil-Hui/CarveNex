/**
 * 转码脚本共享模块：FFmpeg 可执行文件定位 + 视频编码标签探测。
 *
 * 此前各转码脚本各自复制了一份完全相同的 FFMPEG 定位块与 codecOf 实现，
 * 现统一到此，仅保留一种规范实现。
 *
 * - FFMPEG：优先环境变量 FFMPEG_BIN；否则用 imageio_ffmpeg 解析。
 * - Python 解释器：优先环境变量 FFMPEG_PYTHON，默认取本机 workbuddy 环境。
 */
const { execFileSync } = require('child_process')
const fs = require('fs')

const PYTHON =
  process.env.FFMPEG_PYTHON ||
  'C:/Users/peixi/.workbuddy/binaries/python/envs/default/Scripts/python.exe'

/** FFmpeg 可执行文件路径 */
const FFMPEG =
  process.env.FFMPEG_BIN ||
  execFileSync(PYTHON, ['-c', 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())'], {
    encoding: 'utf8',
  }).trim()

/** H.264 编码标签：浏览器全兼容，命中即无需转码 */
const H264 = 'avc1'
const CODEC_TAGS = ['av01', 'hev1', 'hvc1', 'avc1']
const SCAN_BYTES = 64 * 1024

/**
 * 探测视频编码标签。
 * 同时扫描头部（faststart 的 moov 在前）与尾部（普通 mp4 的 moov 在后），
 * 覆盖两种既有实现的判定范围；无法识别时返回 'unknown'（按未转码处理，等价于需转码）。
 */
const codecOf = (file) => {
  const size = fs.statSync(file).size
  const len = Math.min(SCAN_BYTES, size)
  const fd = fs.openSync(file, 'r')
  try {
    const head = Buffer.alloc(len)
    fs.readSync(fd, head, 0, len, 0)
    const tail = size > len ? Buffer.alloc(len) : null
    if (tail) fs.readSync(fd, tail, 0, len, size - len)
    for (const tag of CODEC_TAGS) {
      if (head.indexOf(tag) !== -1 || (tail && tail.indexOf(tag) !== -1)) return tag
    }
    return 'unknown'
  } finally {
    fs.closeSync(fd)
  }
}

module.exports = { FFMPEG, codecOf, H264, CODEC_TAGS }
