/* 把「laserpeck 应用场景」下的非 H.264（AV1 等）视频就地转码为 H.264。
 * 该目录是唯一视频文件夹，不再另存备份副本（历史 backups/laserpeck-av1 已删除）。
 * 视频源目录 / FFmpeg 定位统一取自共享模块，不再各自硬编码。 */
const { execFileSync } = require('child_process')
const fs = require('fs')
const path = require('path')
const { FFMPEG, codecOf, H264 } = require('./lib/ffmpeg.cjs')
const { SCENARIO_VIDEO_DIR: SRC } = require('../scenario-videos.config.cjs')

const walk = (dir, out = []) => {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name)
    if (entry.isDirectory()) walk(p, out)
    else if (/\.(mp4|mov|webm|m4v)$/i.test(entry.name) && !entry.name.endsWith('.tmp.mp4')) out.push(p)
  }
  return out
}

let done = 0
let skipped = 0
for (const file of walk(SRC)) {
  const rel = path.relative(SRC, file)
  const codec = codecOf(file)
  if (codec === H264) {
    skipped++
    console.log(`skip  ${rel}`)
    continue
  }
  const tmp = file + '.h264.tmp.mp4'
  console.log(`trans ${rel} (${codec} -> ${H264}) ...`)
  execFileSync(FFMPEG, [
    '-y', '-i', file,
    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
    '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
    '-c:a', 'aac', '-b:a', '128k',
    tmp,
  ], { stdio: ['ignore', 'ignore', 'pipe'] })
  // 沙箱不允许 rename 覆盖已存在文件 → copyFileSync 覆盖后删除临时文件
  fs.copyFileSync(tmp, file)
  fs.unlinkSync(tmp)
  done++
  console.log(`done  ${rel}`)
}
console.log(`ALL DONE: ${done} transcoded, ${skipped} skipped (already H.264)`)
