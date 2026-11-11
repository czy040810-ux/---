const {request,requireLogin,fail}=require('../../utils/api')
Page({
  data:{items:[],shown:[],tags:['全部'],active:'全部',dueOnly:false},
  onShow(){if(requireLogin())this.load()},
  async load(){
    try{
      const list=await request('GET','/questions')
      const items=list.map(x=>({...x,short:x.text.slice(0,48),dueLabel:x.due.slice(0,10),isDue:Date.parse(x.due)<=Date.now()}))
      this.setData({items,tags:['全部',...new Set(items.map(x=>x.tag))]})
      this.filter()
    }catch(e){fail(e)}
  },
  pickTag(e){this.setData({active:e.currentTarget.dataset.tag});this.filter()},
  toggleDue(e){this.setData({dueOnly:e.detail.value});this.filter()},
  filter(){
    this.setData({shown:this.data.items.filter(x=>(this.data.active==='全部'||x.tag===this.data.active)&&(!this.data.dueOnly||x.isDue))})
  },
  detail(e){wx.navigateTo({url:'/pages/detail/index?id='+e.currentTarget.dataset.id})}
})
