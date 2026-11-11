"""接口冒烟测试：使用临时数据库，不触碰实际演示数据。"""
import os
import subprocess
import sys


def test_flow(tmp_path):
    # 在独立复制的最小运行目录中启动，不影响真实数据库。
    import shutil
    root = tmp_path / "sample"
    shutil.copytree(os.path.join(os.path.dirname(__file__), "..", "backend"), root / "backend")
    test_code = r'''
from fastapi.testclient import TestClient
from backend.main import app
from backend.services import copyright_check, next_review
c = TestClient(app)
def reg(name):
    assert c.post('/register', json={'username':name,'password':'password123'}).status_code == 200
    return c.post('/login',json={'username':name,'password':'password123'}).json()['token']
a,b=reg('student_a'),reg('student_b')
ha={'Authorization':'Bearer '+a}; hb={'Authorization':'Bearer '+b}
res=c.post('/questions',headers=ha,json={'text':'已知 x+1=3，求 x。','tag':'方程'}); assert res.status_code==200,res.text
qid=res.json()['id']
assert len(c.get('/questions',headers=ha).json())==1
assert c.get('/questions',headers=hb).json()==[]
assert c.patch('/questions/'+str(qid)+'/tag',headers=hb,json={'tag':'偷改'}).status_code==404
assert c.get('/public').json()==[]
assert c.post('/questions/'+str(qid)+'/submit',headers=ha).json()['status']=='pending'
assert c.get('/public').json()==[]
admin=c.post('/login',json={'username':'teacher','password':'secure_pass_123'}).json()['token']
had={'Authorization':'Bearer '+admin}
assert len(c.get('/admin/pending',headers=had).json())==1
assert c.post('/admin/'+str(qid),headers=had,json={'approved':True}).status_code==200
assert len(c.get('/public').json())==1
assert c.get('/admin/pending',headers=hb).status_code==403
assert copyright_check('付费教辅原题','未知')[0]=='rejected'
assert next_review(0,True)[0]==1
assert next_review(4,False)[0]==0
'''
    env = dict(os.environ, ADMIN_USER="teacher", ADMIN_PASSWORD="secure_pass_123")
    result = subprocess.run([sys.executable, "-c", test_code], cwd=root, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
