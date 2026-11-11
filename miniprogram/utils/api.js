const { BASE_URL } = require('../config')

// 统一封装 API：会话过期时清理本地凭据，不向日志输出 token。
function request(method, path, data) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: BASE_URL + path, method,
      data: data || {},
      header: { 'Authorization': 'Bearer ' + (wx.getStorageSync('token') || '') },
      timeout: 30000,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) return resolve(res.data)
        if (res.statusCode === 401 && path !== '/login') {
          wx.removeStorageSync('token')
          wx.reLaunch({ url: '/pages/login/index' })
        }
        reject(new Error((res.data && res.data.detail) || `请求失败：${res.statusCode}`))
      },
      fail() { reject(new Error('网络连接失败，请检查 HTTPS 域名及服务状态')) }
    })
  })
}

// 只将临时图片路径上传给后端；大模型密钥和数据库不进入小程序包。
function uploadPhoto(filePath) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: BASE_URL + '/ocr', filePath, name: 'file',
      header: { 'Authorization': 'Bearer ' + (wx.getStorageSync('token') || '') },
      timeout: 30000,
      success(res) {
        if (res.statusCode === 401) {
          wx.removeStorageSync('token')
          wx.reLaunch({ url: '/pages/login/index' })
        }
        if (res.statusCode < 200 || res.statusCode >= 300) return reject(new Error('上传失败'))
        try { resolve(JSON.parse(res.data)) } catch (_) { reject(new Error('识别响应有误')) }
      },
      fail() { reject(new Error('图片上传失败，请检查网络')) }
    })
  })
}

function requireLogin() {
  if (wx.getStorageSync('token')) return true
  wx.navigateTo({ url:'/pages/login/index' })
  return false
}

function fail(error) { wx.showToast({ title:error.message || '操作失败', icon:'none', duration:2500 }) }

module.exports = { request, uploadPhoto, requireLogin, fail }
