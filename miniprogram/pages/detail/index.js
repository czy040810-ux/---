const {request,fail}=require('../../utils/api')
Page({
  data:{id:0,item:null,tag:'',answerVisible:false,busy:false},
  onLoad(options){this.setData({id:Number(options.id)});this.load()},
  async load(){
    try{
      // 后端仅返回当前用户的私有错题；无法凭 URL 读取他人内容。
      const list=await request('GET','/questions')
      const item=list.find(x=>x.id===this.data.id)
      if(!item)return wx.showToast({title:'无权访问或题目不存在',icon:'none'})
      this.setData({item:{...item,dueLabel:item.due.slice(0,10)},tag:item.tag})
    }catch(e){fail(e)}
  },
  setTag(e){this.setData({tag:e.detail.value})},
  showAnswer(){this.setData({answerVisible:!this.data.answerVisible})},
  async editTag(){
    try{await request('PATCH',`/questions/${this.data.id}/tag`,{tag:this.data.tag});wx.showToast({title:'标签已保存'});this.load()}catch(e){fail(e)}
  },
  async review(e){
    if(this.data.busy)return
    this.setData({busy:true})
    try{
      const remembered=e.currentTarget.dataset.yes===true
      const result=await request('POST',`/questions/${this.data.id}/review?remembered=${remembered}`)
      wx.showModal({title:'复习已记录',content:`下次复习：${result.due.slice(0,10)}`,showCancel:false})
      this.load()
    }catch(e){fail(e)}finally{this.setData({busy:false})}
  },
  async submit(){
    try{
      const result=await request('POST',`/questions/${this.data.id}/submit`)
      wx.showModal({title:result.status==='rejected'?'自动初审驳回':'提交成功',content:result.note,showCancel:false})
      this.load()
    }catch(e){fail(e)}
  }
})
