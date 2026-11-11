const { request, fail } = require('../../utils/api')
Page({
  data: { mode:'login', username:'', password:'', busy:false },
  setMode(e) { this.setData({ mode:e.currentTarget.dataset.mode }) },
  setUser(e) { this.setData({ username:e.detail.value }) },
  setPassword(e) { this.setData({ password:e.detail.value }) },
  async submit() {
    if (this.data.busy) return
    const {username,password,mode} = this.data
    if (username.trim().length < 2 || password.length < 8) return wx.showToast({title:'用户名至少2位、密码至少8位',icon:'none'})
    this.setData({busy:true})
    try {
      if (mode === 'register') {
        await request('POST','/register',{username,password})
        wx.showToast({title:'注册成功，请登录',icon:'none'})
        this.setData({mode:'login',password:''})
      } else {
        const res = await request('POST','/login',{username,password})
        wx.setStorageSync('token',res.token)
        wx.setStorageSync('role',res.role)
        getApp().globalData.role = res.role
        wx.switchTab({url:'/pages/home/index'})
      }
    } catch(e) { fail(e) } finally { this.setData({busy:false}) }
  }
})
