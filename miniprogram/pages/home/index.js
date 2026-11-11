const { request, requireLogin, fail } = require('../../utils/api')
Page({
  data:{ count:0,due:0,tags:0,role:'user' },
  onShow(){ if (requireLogin()) this.load() },
  async load(){
    try {
      const list = await request('GET','/questions')
      this.setData({
        count:list.length,
        due:list.filter(x=>Date.parse(x.due)<=Date.now()).length,
        tags:new Set(list.map(x=>x.tag)).size,
        role:wx.getStorageSync('role')||'user'
      })
    } catch(e){ fail(e) }
  },
  capture(){ wx.switchTab({url:'/pages/capture/index'}) },
  review(){ wx.switchTab({url:'/pages/book/index'}) },
  admin(){ wx.navigateTo({url:'/pages/admin/index'}) },
  async logout(){
    try { await request('POST','/logout') } catch (_) {}
    wx.removeStorageSync('token');wx.removeStorageSync('role')
    wx.reLaunch({url:'/pages/login/index'})
  }
})
