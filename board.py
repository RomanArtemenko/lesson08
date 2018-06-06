from flask import Flask, jsonify, request

ads = [{
    'id':1,
    'user':'test_user_1',
    'title':'test title #1',
    'date':'2018-05-01 12:13',
    'comments':[{
        'id':1,
        'user':'test_user_2',
        'text':'test comment #1',
        'date':'2018-05-04 13:43'
    }]
},
{
    'id':2,
    'user':'test_user_11',
    'title':'test title #2',
    'date':'2018-04-05 02:53',
    'comments':[{
        'id':1,
        'user':'test_user_12',
        'text':'test comment #22',
        'date':'2018-05-04 13:43'
    },
    {
        'id':2,
        'user':'test_user_132',
        'text':'test comment #23',
        'date':'2018-07-03 03:41'
    }]
}]

app = Flask(__name__)

@app.route('/ads', methods=["GET"])
def ad_list():
    return jsonify({"ads": ads})

@app.route('/ads/<int:id>', methods=["GET"])
def ad(id):
    if request.method == 'GET':
        return jsonify({"ads": ads[id - 1]})
        # return 'This is a GET'

if __name__ == '__main__':
    app.run(debug=True)