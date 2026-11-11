const {request,fail}=require('../../utils/api')
Page({
  data:{items:[],notes:{}},
  onShow(){this.load()},
  async load(){
    try{this.setData({items:await request('GET','/admin/pending')})}catch(e){fail(e)}
  },
  setNote(e){this.setData({[`notes.${e.currentTarget.dataset.id}`]:e.detail.value})},
  decide(e){
    const id=e.currentTarget.dataset.id,approved=e.currentTarget.dataset.approved===true
    wx.showModal({title:approved?'确认审核通过？':'确认驳回？',content:'请先确认内容来源、版权与个人信息风险。',success:async(res)=>{
      if(!res.confirm)return
      try{
        await request('POST',`/admin/${id}`,{approved,note:this.data.notes[id]||''})
        wx.showToast({title:'审核已完成'});this.load()
      }catch(err){fail(err)}
    }})
  }
})
