// 小程序全局状态：不在客户端保存管理员密码或 API 密钥。
App({
  globalData: { role: wx.getStorageSync('role') || 'user' },
  onLaunch() {
    // 启动时只恢复登录标记；接口会再次验证会话是否有效。
    this.globalData.role = wx.getStorageSync('role') || 'user'
  }
})
