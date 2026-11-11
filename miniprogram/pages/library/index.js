const {request,fail}=require('../../utils/api')
Page({
  data:{items:[],shown:[],tags:['全部'],active:'全部',opened:0},
  onShow(){this.load()},
  async load(){
    try{
      const items=await request('GET','/public')
      this.setData({items,tags:['全部',...new Set(items.map(x=>x.tag))]});this.filter()
    }catch(e){fail(e)}
  },
  pick(e){this.setData({active:e.currentTarget.dataset.tag});this.filter()},
  filter(){this.setData({shown:this.data.items.filter(x=>this.data.active==='全部'||x.tag===this.data.active)})},
  toggle(e){const id=e.currentTarget.dataset.id;this.setData({opened:this.data.opened===id?0:id})}
})
